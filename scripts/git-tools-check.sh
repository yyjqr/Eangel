##解决git pre-commit设置后，代码提交错误
#这个错误是由于 virtualenv 和 setuptools 版本不兼容导致的。核心问题是系统的 virtualenv (旧版) 与用户安装的 setuptools (新版) 发生冲突。

pip3 install --user --upgrade virtualenv
