#-------------------------------------------------
#
# Project created by QtCreator 2017-10-17T16:07:37
#
#-------------------------------------------------

QT       += core gui network

greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = RobotCam
TEMPLATE = app


SOURCES += main.cpp\
        logging.cpp \
        mainwindow.cpp

HEADERS  += mainwindow.h \
    logging.h

FORMS    += mainwindow.ui
