# SfM (COLMAP via pycolmap) for each plant WITHOUT board poses (user idea, 2026-09-27), then a similarity alignment to
# the board frame through the board-posed photos. Reports registered photos, points, reprojection error, and how far
# the SfM cameras land from the board poses (fit on all posed photos, and leave-one-out). CPU kernel.
import glob, json, os, shutil, subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pycolmap"], check=True)
from pathlib import Path
import cv2, numpy as np, pycolmap

hits = [p for p in glob.glob("/kaggle/input/**/index.json", recursive=True) if json.load(open(p)).get("schema") == "sfm-input-1"]
assert hits, "sfm-input-1 not found"
SRC = Path(os.path.dirname(hits[0])); RESULT = "/kaggle/working/sfm_results.json"
ALL = json.load(open(RESULT)) if os.path.exists(RESULT) else {}

def similarity(A, B):
    ma, mb = A.mean(0), B.mean(0); U, S, Vt = np.linalg.svd((A - ma).T @ (B - mb)); D = np.eye(3)
    if np.linalg.det(Vt.T @ U.T) < 0: D[2, 2] = -1
    R = Vt.T @ D @ U.T; s = np.trace(np.diag(S) @ D) / ((A - ma) ** 2).sum()
    return s, R, mb - s * R @ ma

for plant in json.load(open(SRC / "index.json"))["plants"]:
    if plant in ALL and "error" not in ALL[plant]: continue
    try:
        work = Path("/kaggle/working") / f"sfm_{plant}"; shutil.rmtree(work, ignore_errors=True); (work / "images").mkdir(parents=True)
        cap = json.load(open(SRC / plant / "capture.json", encoding="utf-8"))
        for f in cap["frames"]:
            shutil.copy(SRC / plant / "images" / (Path(f["image_file"]).stem + ".jpg"), work / "images")
        K = np.array(cap["intrinsics"]["camera_matrix"]); Dd = np.array(cap["intrinsics"]["dist_coeffs"]).ravel()
        reader = pycolmap.ImageReaderOptions(); reader.camera_model = "OPENCV"
        reader.camera_params = ",".join(f"{v:.6f}" for v in [K[0, 0], K[1, 1], K[0, 2], K[1, 2], Dd[0], Dd[1], Dd[2], Dd[3]])
        ext = pycolmap.FeatureExtractionOptions(); ext.max_image_size = 3200
        ext.sift.max_num_features = 16000; ext.sift.estimate_affine_shape = True; ext.sift.domain_size_pooling = True
        db = work / "db.db"
        pycolmap.extract_features(db, work / "images", camera_mode=pycolmap.CameraMode.SINGLE, reader_options=reader, extraction_options=ext)
        mo = pycolmap.FeatureMatchingOptions(); mo.guided_matching = True
        pycolmap.match_exhaustive(db, matching_options=mo)
        opts = pycolmap.IncrementalPipelineOptions()
        opts.ba_refine_focal_length = False; opts.ba_refine_extra_params = False; opts.ba_refine_principal_point = False
        recs = pycolmap.incremental_mapping(db, work / "images", work / "sparse", options=opts)
        if not recs:
            ALL[plant] = dict(registered=0); continue
        rec = max(recs.values(), key=lambda r: r.num_reg_images())
        out = dict(models=len(recs), registered=rec.num_reg_images(), of=len(cap["frames"]), points=rec.num_points3D(),
                   mean_reproj_px=round(rec.compute_mean_reprojection_error(), 3))
        sfm = {}
        for img in rec.images.values():
            if not img.has_pose: continue
            T = img.cam_from_world() if callable(img.cam_from_world) else img.cam_from_world
            R = T.rotation.matrix(); t = np.asarray(T.translation)
            sfm[Path(img.name).stem[-2:]] = (R, -R.T @ t)
        board = {}
        for f in cap["frames"]:
            if f["pose_status"] == "solved" and f.get("rvec_rad"):
                R = cv2.Rodrigues(np.array(f["rvec_rad"]))[0]; board[f["view_code"]] = (R, -R.T @ np.array(f["tvec_mm"]))
        out["registered_views"] = sorted(sfm); out["board_views"] = sorted(board)
        common = [v for v in board if v in sfm]
        if len(common) >= 3:
            s, Rs, ts = similarity(np.array([sfm[v][1] for v in common]), np.array([board[v][1] for v in common]))
            vs = {}
            for v in common:
                ang = np.degrees(np.arccos(np.clip((np.trace((sfm[v][0] @ Rs.T) @ board[v][0].T) - 1) / 2, -1, 1)))
                vs[v] = dict(centre_diff_mm=round(float(np.linalg.norm(s * Rs @ sfm[v][1] + ts - board[v][1])), 2), rot_diff_deg=round(float(ang), 3))
            out["vs_board_fit_all"] = vs
            if len(common) >= 4:
                loo = {}
                for h in common:
                    rest = [v for v in common if v != h]
                    s2, R2, t2 = similarity(np.array([sfm[v][1] for v in rest]), np.array([board[v][1] for v in rest]))
                    loo[h] = round(float(np.linalg.norm(s2 * R2 @ sfm[h][1] + t2 - board[h][1])), 2)
                out["leave_one_out_centre_err_mm"] = loo
            out["new_views_in_board_frame"] = {v: [round(float(x), 1) for x in (s * Rs @ sfm[v][1] + ts)] for v in sfm if v not in board}
        ALL[plant] = out
        shutil.rmtree(work / "images", ignore_errors=True)
    except Exception as e:
        ALL[plant] = dict(error=repr(e))
    json.dump(ALL, open(RESULT, "w"), indent=1); print(plant, json.dumps(ALL[plant])[:600], flush=True)
print(json.dumps(ALL, indent=1))
