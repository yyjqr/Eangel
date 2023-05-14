#include "qdisplay.h"
#include <QPainter>
QDisplay::QDisplay(QWidget *parent) :
    QWidget(parent)
{

}

void QDisplay::displayImage(QImage img)
{
    QSize sz = this->size();
    data = img.scaled(sz,Qt::KeepAspectRatio);
    update();
}

void QDisplay::paintEvent(QPaintEvent *event)
{
    QPainter painter(this);
    painter.setBrush(Qt::white);

    int x = this->width() - data.width();
    int y = this->height() - data.height();

    x /= 2;
    y /= 2;
    painter.drawImage(QPoint(x,y),data);
}

void QDisplay::resizeEvent(QResizeEvent *event)
{

}
