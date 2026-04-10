FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 && \
    rm -rf /var/lib/apt/lists/*

# Explicit CUDA arch list for PyTorch
ARG TORCH_CUDA_ARCH_LIST="8.9"
ENV TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}

WORKDIR /app

# Hunyuan3D-2 setup
ARG HUNYUAN3D_COMMIT=f8db63096c8282cb27354314d896feba5ba6ff8a
RUN git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git Hunyuan3D-2 && \
    cd Hunyuan3D-2 && \
    git checkout ${HUNYUAN3D_COMMIT} && \
    rm -rf .git

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
