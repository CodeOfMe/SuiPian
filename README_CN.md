# SuiPian (碎片)

将任意文件用零宽字符编码为纯文本，看起来完全正常，只有密钥才能还原。

## 原理

1. **压缩**: LZ4 压缩源文件
2. **加密**: AES-256-GCM + PBKDF2 密钥派生（10万次迭代）
3. **编码**: 将加密后的二进制数据编码为零宽字符（​‌U+200B / ​‌U+200C）
4. **拼接**: 零宽字符串追加到载体文本末尾，对外呈现完全正常的文本

**无法被检测**: 无任何特殊标记、无 Base64 可见字符、零宽字符在大多数编辑器中完全隐形。

## 功能特点

- **Hide**: 将任意文件（图片、文档等）编码为看似普通的文本文件
- **Reveal**: 使用密码从伪装文本中还原原始文件
- **Validate**: 检查文本中是否藏有数据
- **Info**: 获取隐藏数据的元信息

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

隐藏文件（图片 → 文本）：
```bash
suipian hide photo.png article.txt -o output.txt -p mypassword
```

还原文件（文本 → 图片）：
```bash
suipian reveal output.txt -o restored.png -p mypassword
```

验证是否藏有数据：
```bash
suipian validate output.txt
```

查看隐藏文件信息：
```bash
suipian info output.txt
```

### Python API

```python
from suipian import hide_file, reveal_file, validate_morph

result = hide_file(
    source="photo.png",
    carrier="article.txt",
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