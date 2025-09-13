#!/bin/bash

ARCH=$(uname -m)

if [[ "$ARCH" == "x86_64" ]]; then
    echo "Installing onnxruntime-gpu"
    pip install onnxruntime-gpu
elif [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    echo "Installing onnxruntime"
    pip install onnxruntime
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi
