from setuptools import setup, find_packages
import os

# 读取版本信息
def read_version():
    with open(os.path.join(os.path.dirname(__file__), 'VERSION')) as f:
        return f.read().strip()

setup(
    name="openrhythm",
    version=read_version(),
    packages=find_packages(),
    install_requires=[
        "pygame>=2.5.0",  # 用于基础输入和窗口测试
        "numpy>=1.24.0",
        "toml>=0.10.0",
    ],
    python_requires=">=3.8",
)