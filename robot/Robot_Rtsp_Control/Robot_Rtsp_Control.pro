QT       += core gui network
##add network  for QtcpSocket
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

CONFIG += c++11

# You can make your code fail to compile if it uses deprecated APIs.
# In order to do so, uncomment the following line.
#DEFINES += QT_DISABLE_DEPRECATED_BEFORE=0x060000    # disables all the APIs deprecated before Qt 6.0.0

SOURCES += \
    main.cpp \
    mainwindow.cpp \
    qdisplay.cpp \
    videoplayer.cpp\
    logging.cpp

HEADERS += \
    mainwindow.h \
    qdisplay.h \
    videoplayer.h \
    logging.h

FORMS += \
    mainwindow.ui




INCLUDEPATH += $$PWD/ffmpeg-4.4/include
#                $$PWD/src
INCLUDEPATH +=$$PWD/include

## minGW64 编译的静态库
LIBS += $$PWD/ffmpeg-4.4/libs/avcodec.lib \
        $$PWD/ffmpeg-4.4/libs/avdevice.lib \
        $$PWD/ffmpeg-4.4/libs/avfilter.lib \
        $$PWD/ffmpeg-4.4/libs/avformat.lib \
        $$PWD/ffmpeg-4.4/libs/avutil.lib \
        $$PWD/ffmpeg-4.4/libs/postproc.lib \
        $$PWD/ffmpeg-4.4/libs/swresample.lib \
        $$PWD/ffmpeg-4.4/libs/swscale.lib

#FFMPEG_HOME=D:/qt-GUI/ffmpeg_qt_rtsp/ffmpeg-4.4/import-lib

#LIBS +=  -L$$FFMPEG_HOME/lib \
#                 -lavcodec \
#                 -lavdevice \
#                 -lavfilter \
#                -lavformat \
#                -lavutil \
#                -lpostproc \
#                -lswresample \
#                -lswscale

greaterThan(QT_MAJOR_VERSION,5):QT+=core5compat

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target
