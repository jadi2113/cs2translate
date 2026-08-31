python -m nuitka \
    --onefile \
    --output-filename=cs2translate \
    --enable-plugin=tk-inter \
    --windows-console-mode=hide \
    --lto=yes \
    --output-dir=build \
    cs2translate

cp -f autolaunch.bat build/autolaunch.bat
cp -f autolaunch.sh build/autolaunch.sh
