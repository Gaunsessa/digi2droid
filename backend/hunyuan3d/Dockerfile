FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /app

# Hunyuan3D-2 setup
COPY Hunyuan3D-2/ ./Hunyuan3D-2/

RUN set -euxo pipefail && cd Hunyuan3D-2 && \
    echo "=== [1/4] pip install -r requirements.txt ===" && \
    pip install --no-cache-dir -v -r requirements.txt

RUN set -euxo pipefail && cd Hunyuan3D-2 && \
    echo "=== [2/4] pip install -e . (hy3dgen) ===" && \
    pip install --no-cache-dir -v -e .

RUN set -euxo pipefail && cd Hunyuan3D-2/hy3dgen/texgen/custom_rasterizer && \
    echo "=== [3/4] custom_rasterizer (CUDAExtension) ===" && \
    python3 setup.py build_ext --verbose && \
    python3 setup.py install

RUN set -euxo pipefail && cd Hunyuan3D-2/hy3dgen/texgen/differentiable_renderer && \
    echo "=== [4/4] differentiable_renderer (pybind11 / mesh_processor) ===" && \
    python3 setup.py build_ext --verbose && \
    python3 setup.py install

# Handler setup
COPY handler.py .

CMD ["python", "-u", "handler.py"]