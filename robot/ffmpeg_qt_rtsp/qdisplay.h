#ifndef QDISPLAY_H
#define QDISPLAY_H

#include <QWidget>

class QDisplay : public QWidget
{
    Q_OBJECT
public:
    QDisplay(QWidget *parent);
    void displayImage(QImage data);

protected:
    void paintEvent(QPaintEvent *event);
    void resizeEvent(QResizeEvent *event);
    QImage data;

};

#endif // QDISPLAY_H
