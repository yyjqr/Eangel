#ifndef VIDEOPLAYER_H
#define VIDEOPLAYER_H

#include <QThread>
#include <QImage>
#include <QWidget>
#include <QMutex>
#include <QWaitCondition>


extern "C"
{
    #include "libavcodec/avcodec.h"
    #include "libavformat/avformat.h"
    #include "libavutil/pixfmt.h"
//swscale:视频像素数据格式转换
    #include "libswscale/swscale.h"


    //avdevice:各种设备的输入输出
    #include "libavdevice/avdevice.h"
    //avutil:工具库（大部分库都需要这个库的支持）
    #include "libavutil/avutil.h"

}

enum State
{
    Stoped,     ///<停止状态，包括从未启动过和启动后被停止
    Running,    ///<运行状态
    Paused      ///<暂停状态
};



class VideoPlayer: public QThread
{
    Q_OBJECT
public:
    VideoPlayer();
    ~VideoPlayer();

    void startPlay();
    void stopPlay();
    void pause();
    void resume();

    void setFileName(QString name);
    QString getFileName();

    State state();
    QString getCurrentTime();
signals:
    void sig_GetOneFrame(QImage); //每获取到一帧图像 就发送此信号
    void sig_GetRFrame(QImage);   ///2017.8.11---lizhen

protected:
    void run();
private:
    QString mFileName = "";
    QMutex mutex;
    QWaitCondition condition;
    std::atomic_bool pauseFlag;
    std::atomic_bool stopFlag;
    int m_not_get_times;
    QString m_timeStr;
};

#endif // VIDEOPLAYER_H

