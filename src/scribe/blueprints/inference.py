from __future__ import annotations

import logging
import multiprocessing
import os
import uuid

from flask import Blueprint, abort, current_app, jsonify, request, send_file

from scribe.utils.file_utils import temp_zip
from scribe.utils.tts_utils.synthesis import (
    text_to_speech,
    tts_with_vc,
    voice_conversion,
)

logger = logging.getLogger(__name__)


inference_blueprint = Blueprint("tasks", __name__)


# wrappers for threading/multiprocessing
def _text_to_speech(text, model, language, speaker, output_path, speaker_wav, stop_event):
    text_to_speech(text, model, language=language, speaker=speaker, output_path=output_path, speaker_wav=speaker_wav)
    stop_event.set()


def _tts_with_vc(text, model, language, speaker, output_path, speaker_wav, stop_event):
    tts_with_vc(text, model, language=language, speaker=speaker, output_path=output_path, speaker_wav=speaker_wav)
    stop_event.set()


def _voice_conversion(source_wav, target_wav, model, output_path, stop_event):
    voice_conversion(source_wav, target_wav, model, output_path)
    stop_event.set()


@inference_blueprint.route("/upload_model", methods=["POST"])
def upload_model():
    """Upload a model to the filesystem."""

    if "model" not in request.files:
        abort(400, "No model file provided.")
    if "type" not in request.form:
        abort(400, "No model type provided.")

    type = request.form["type"]
    filename = request.form.get("filename", request.files["model"].filename)
    filesystem_root = current_app.config["FILESYSTEM_ROOT"]
    if type == "base":
        path = os.path.join(filesystem_root, "models", "base")
    elif type == "vocoder":
        path = os.path.join(filesystem_root, "models", "vocoder")
    else:
        abort(501, "Given model type is not supported yet.")

    request.files["model"].save(os.path.join(path, filename))
    return jsonify({"message": "Model uploaded successfully."})


@inference_blueprint.route("/list_modela", methods=["GET"])
def list_models():
    """List all models in the filesystem."""
    if "type" not in request.form:
        abort(400, "No model type provided.")
    type = request.form["type"]

    filesystem_root = current_app.config["FILESYSTEM_ROOT"]
    if type == "base":
        path = os.path.join(filesystem_root, "models", "base")
    elif type == "vocoder":
        path = os.path.join(filesystem_root, "models", "vocoder")
    else:
        abort(501, "Given model type is not supported yet.")

    models = os.listdir(path)
    return jsonify({"models": models})


@inference_blueprint.route("/delete_model", methods=["DELETE"])
def delete_model():
    """Delete a model from the filesystem."""
    if "type" not in request.form:
        abort(400, "No model type provided.")
    if "filename" not in request.form:
        abort(400, "No model filename provided.")

    type = request.form["type"]
    filename = request.form["filename"]
    filesystem_root = current_app.config["FILESYSTEM_ROOT"]
    if type == "base":
        path = os.path.join(filesystem_root, "models", "base")
    elif type == "vocoder":
        path = os.path.join(filesystem_root, "models", "vocoder")
    else:
        abort(501, "Given model type is not supported yet.")

    os.remove(os.path.join(path, filename))
    return jsonify({"message": "Model deleted successfully."})


@inference_blueprint.route("/download_model", methods=["GET"])
def download_model():
    """Download a model from the filesystem."""
    if "type" not in request.form:
        abort(400, "No model type provided.")
    if "filename" not in request.form:
        abort(400, "No model filename provided.")

    type = request.form["type"]
    filename = request.form["filename"]
    filesystem_root = current_app.config["FILESYSTEM_ROOT"]
    if type == "base":
        path = os.path.join(filesystem_root, "models", "base")
    elif type == "vocoder":
        path = os.path.join(filesystem_root, "models", "vocoder")
    else:
        abort(501, "Given model type is not supported yet.")
    path = os.path.join(path, filename)
    zip_path = temp_zip(path)
    response = send_file(zip_path, as_attachment=True, attachment_filename=f"{filename}.zip")
    try:
        os.unlink(zip_path)
    except Exception as e:
        logger.warning(f"Failed to delete temp zip file: {e}")
    return response


@inference_blueprint.route("/synthesize", methods=["POST"])
def synthesize():
    """Synthesize speech from text."""
    if "text" not in request.form:
        abort(400, "No text provided.")
    if "model" not in request.form:
        abort(400, "No model provided.")

    text = request.form["text"]
    model = request.form["model"]
    language = request.form.get("language", "en")
    speaker = request.form.get("speaker", None)
    output_path = request.form.get("output_path", None)
    speaker_wav = request.form.get("speaker_wav", None)
    str(uuid.uuid4())


def synthesize_worker():
    return


@inference_blueprint.route("/voice_conversion", methods=["POST"])
def voice_conversion():
    """Convert voice from source to target."""
    if "source_wav" not in request.form:
        abort(400, "No source wav provided.")
    if "target_wav" not in request.form:
        abort(400, "No target wav provided.")
    if "model" not in request.form:
        abort(400, "No model provided.")

    source_wav = request.form["source_wav"]
    target_wav = request.form["target_wav"]
    model = request.form["model"]
    output_path = request.form.get("output_path", None)
    wav = voice_conversion(source_wav, target_wav, model, output_path)
    return send_file(wav, mimetype="audio/wav")
