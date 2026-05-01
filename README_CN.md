# SuiPian (碎片)

文件伪装与恢复工具 - 将文件藏匿于众目睽睽之下。

将任意文件拆散伪装成看似普通的文本文件，再用密码还原。

## 功能特点

- **隐藏**: 将任意文件（图片、文档等）嵌入到一个看似普通的文本文件中
- **恢复**: 使用密码从伪装文件中还原原始文件
- **验证**: 检查文件是否为有效的伪装文件
- **信息**: 获取伪装文件的元数据

## 系统要求

- Python 3.10+
- lz4
- cryptography

## 安装

```bash
pip install suipian
```

或从源码安装：

```bash
pip install -e .
```

## 快速开始

### 命令行

隐藏文件：
```bash
suipian hide image.png readme.txt -o output.txt -p mypassword
```

恢复隐藏文件：
```bash
suipian reveal output.txt -o restored.png -p mypassword
```

验证伪装文件：
```bash
suipian validate output.txt
```

查看信息：
```bash
suipian info output.txt
```

### Python API

```python
from suipian import hide_file, reveal_file, validate_morph

result = hide_file(
    source="image.png",
    carrier="readme.txt",
    output="output.txt",
    password="secret"
)

result = reveal_file(
    morphed="output.txt",
    output="restored.png",
    password="secret"
)

result = validate_morph(file="output.txt")
print(result.success)
print(result.data)
```

## 开发

```bash
pip install -e ".[dev]"
pytest tests/test_unified_api.py -v
```

## 许可证

GPL-3.0