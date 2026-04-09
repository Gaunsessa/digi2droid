FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 && \
    rm -rf /var/lib/apt/lists/*

# Explicit CUDA arch list for PyTorch
ARG TORCH_CUDA_ARCH_LIST="8.9"
ENV TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}

WORKDIR /app

# Hunyuan3D-2 setup
COPY Hunyuan3D-2/ ./Hunyuan3D-2/

RUN cd Hunyuan3D-2 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . && \
    cd hy3dgen/texgen/custom_rasterizer && python3 setup.py install && \
    cd ../differentiable_renderer && python3 setup.py install

# Handler setup
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

CMD ["python", "-u", "handler.py"]
