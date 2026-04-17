# Load from .env file
from dotenv import load_dotenv
load_dotenv()

import os

from flask import Flask, jsonify, request, url_for

import config
from jobs import JobStore


def create_app() -> Flask:
    app = Flask(__name__)
    store = JobStore()

    @app.post("/v1/jobs")
    def create_job():
        body = request.get_json(silent=True) or {}
        camera_name = (body.get("camera_name") or "").strip()
        if not camera_name:
            return jsonify({"error": "camera_name is required"}), 400

        job = store.submit(camera_name)

        status_url = url_for("get_job", job_id=job.job_id, _external=True)
        res = {
            "job_id": job.job_id,
            "status_url": status_url,
        }

        return jsonify(res), 202

    @app.get("/v1/jobs/<job_id>")
    def get_job(job_id: str):
        job = store.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(job.to_dict())

    return app


if __name__ == "__main__":
    missing = config.check_required()
    if missing:
        raise RuntimeError(f"Missing required config: {', '.join(missing)}")

    port = int(os.environ.get("PORT", "5000"))
    create_app().run(host="0.0.0.0", port=port, threaded=True)
