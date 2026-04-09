FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /app

COPY Hunyuan3D-2/ ./Hunyuan3D-2/

RUN cd Hunyuan3D-2 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . && \
    cd hy3dgen/texgen/custom_rasterizer && python3 setup.py install && \
    cd ../differentiable_renderer && python3 setup.py install

COPY handler.py .

CMD ["python", "-u", "handler.py"]
