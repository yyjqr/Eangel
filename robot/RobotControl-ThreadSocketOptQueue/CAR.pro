#-------------------------------------------------
#
# Project created by QtCreator 2017-10-17T16:07:37
#
#-------------------------------------------------

QT       += core gui network

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = RobotCam
TEMPLATE = app

#win32 {
#  DEFINES += QT_NO_DEBUG_OUTPUT

#}
#else{
#  DEFINES += QT_NO_DEBUG_OUTPUT


#}
config += console
INCLUDEPATH +=./include


SOURCES += src/logging.cpp \
        src/controlTCP.cpp \
        src/main.cpp \
        src/mainwindow.cpp \
        src/pictureThread.cpp

HEADERS  +=   src/logging.h \
    src/camSocketParam.h \
    src/controlTCP.h \
    src/mainwindow.h \
    src/pictureThread.h

FORMS    += src/mainwindow.ui

RESOURCES += \
    buttonIcon.qrc
