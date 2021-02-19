#-------------------------------------------------
#
# Project created by QtCreator 2017-10-17T16:07:37
#
#-------------------------------------------------

QT       += core gui network

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = RobotCam
TEMPLATE = app


SOURCES += src/logging.cpp \
        src/main.cpp \
        src/mainwindow.cpp

HEADERS  += src/logging.h \
    src/mainwindow.h

FORMS    += src/mainwindow.ui
