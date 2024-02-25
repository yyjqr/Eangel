#include "videoplayer.h"
#include <QDebug>
#include <QDateTime>
#include <QMessageBox>
#include <QTimer>

VideoPlayer::VideoPlayer()
{
    pauseFlag = false;
    stopFlag = false;
    qDebug()<<"ffmpeg  avcodec version:"<<avcodec_version()<<endl;


}

VideoPlayer::~VideoPlayer()
{
    qDebug()<<"播放器已经释放";
}

void VideoPlayer::startPlay()
{
    ///调用 QThread 的start函数 将会自动执行下面的run函数 run函数是一个新的线程
    this->start();
}

void VideoPlayer::stopPlay()
{
    qDebug()<<getCurrentTime()<<"stopFlag:"<<stopFlag<<endl;
    if (QThread::isRunning())
    {
        stopFlag = true;
        condition.wakeAll();
        QThread::quit();
        QThread::wait();
    }
}

void VideoPlayer::pause()
{
    if (QThread::isRunning())
    {
        pauseFlag = true;
    }
}

void VideoPlayer::resume()
{
    if (QThread::isRunning())
    {
        pauseFlag = false;
        condition.wakeAll();
    }
}

void VideoPlayer::setFileName(QString name)
{
    this->mFileName = name;
}

QString VideoPlayer::getFileName()
{
    return mFileName;
}

State VideoPlayer::state()
{
    State s = Stoped;
    if (!QThread::isRunning())
    {
        s = Stoped;
    }
    else if (QThread::isRunning() && pauseFlag)
    {
        s = Paused;
    }
    else if (QThread::isRunning() && (!pauseFlag))
    {
        s = Running;
    }
    return s;

}

void VideoPlayer::run()
{
    qDebug() << "enter thread : " << QThread::currentThreadId();

    AVFormatContext *pFormatCtx;
    AVCodecContext *pCodecCtx;
    AVCodec *pCodec;
    AVFrame *pFrame, *pFrameRGB;
    AVPacket *packet;
    uint8_t *out_buffer;

    static struct SwsContext *img_convert_ctx;

    int videoStream,numBytes;
    int ret, got_picture;

    av_register_all();         //初始化FFMPEG  调用了这个才能正常适用编码器和解码器

    //Allocate an AVFormatContext.
    pFormatCtx = avformat_alloc_context();

    ///2017.8.5---lizhen
    AVDictionary *avdic=NULL;
    char option_key[]="rtsp_transport";
    char option_value[]="udp";  // tcp -->udp
    av_dict_set(&avdic,option_key,option_value,0);
    char option_key2[]="max_delay";
    char option_value2[]="100";
    av_dict_set(&avdic,option_key2,option_value2,0);

    ///rtsp地址，可根据实际情况修改

    auto Qurl = mFileName.toLatin1();

    char *url = Qurl.data();

    if (avformat_open_input(&pFormatCtx, url, NULL, &avdic) != 0) {
        printf("can't open the file. \n");
        return;
    }

    if (avformat_find_stream_info(pFormatCtx, NULL) < 0) {
        printf("Could't find stream infomation.\n");
        return;
    }

    videoStream = -1;

    ///循环查找视频中包含的流信息，直到找到视频类型的流
    ///便将其记录下来 保存到videoStream变量中
    ///这里我们现在只处理视频流  音频流先不管
    for (int k = 0; k < pFormatCtx->nb_streams; k++) {
        if (pFormatCtx->streams[k]->codec->codec_type == AVMEDIA_TYPE_VIDEO) {
            videoStream = k;
        }
    }

    ///如果videoStream为-1 说明没有找到视频流
    if (videoStream == -1) {
        printf("Didn't find a video stream.\n");
        return;
    }

    ///查找解码器
    pCodecCtx = pFormatCtx->streams[videoStream]->codec;
    pCodec = avcodec_find_decoder(pCodecCtx->codec_id);
    ///2017.8.9---lizhen
    pCodecCtx->bit_rate =0;   //初始化为0
    pCodecCtx->time_base.num=1;  //下面两行：一秒钟25帧
    pCodecCtx->time_base.den=10;
    pCodecCtx->frame_number=1;  //每包一个视频帧

    if (pCodec == NULL) {
        printf("Codec not found.\n");
        return;
    }

    ///打开解码器
    if (avcodec_open2(pCodecCtx, pCodec, NULL) < 0) {
        printf("Could not open codec.\n");
        return;
    }

    pFrame = av_frame_alloc();
    pFrameRGB = av_frame_alloc();

    ///这里我们改成了 将解码后的YUV数据转换成RGB32
    img_convert_ctx = sws_getContext(pCodecCtx->width, pCodecCtx->height,
            pCodecCtx->pix_fmt, pCodecCtx->width, pCodecCtx->height,
            AV_PIX_FMT_RGB32, SWS_BICUBIC, NULL, NULL, NULL);

    numBytes = avpicture_get_size(AV_PIX_FMT_RGB32, pCodecCtx->width,pCodecCtx->height);

    out_buffer = (uint8_t *) av_malloc(numBytes * sizeof(uint8_t));
    avpicture_fill((AVPicture *) pFrameRGB, out_buffer, AV_PIX_FMT_RGB32,
            pCodecCtx->width, pCodecCtx->height);

    int y_size = pCodecCtx->width * pCodecCtx->height;

    packet = (AVPacket *) malloc(sizeof(AVPacket)); //分配一个packet
    av_new_packet(packet, y_size); //分配packet的数据

    while (!stopFlag)
    {
        if (pauseFlag)
        {
            mutex.lock();
            condition.wait(&mutex);
            mutex.unlock();
        }
        if (av_read_frame(pFormatCtx, packet) < 0)
        {
            qDebug()<<"read frame over!!!"<<endl;
            break; //这里认为视频读取完了
        }

        if (packet->stream_index == videoStream) {
            ret = avcodec_decode_video2(pCodecCtx, pFrame, &got_picture,packet);

            if (ret < 0) {
                printf("decode error.\n");
                return;
            }

            if (got_picture) {
                sws_scale(img_convert_ctx,
                        (uint8_t const * const *) pFrame->data,
                        pFrame->linesize, 0, pCodecCtx->height, pFrameRGB->data,
                        pFrameRGB->linesize);
                //把这个RGB数据 用QImage加载
                QImage tmpImg((uchar *)out_buffer,pCodecCtx->width,pCodecCtx->height,QImage::Format_RGB32);
                QImage image = tmpImg.copy(); //把图像复制一份 传递给界面显示
                emit sig_GetOneFrame(image);  //发送信号
            }
            else
            {
                m_not_get_times++;
                if(m_not_get_times >3)
                {
                    qDebug()<<getCurrentTime()<<"not get frame!!!"<<endl;
                    QMessageBox*  box = new   QMessageBox(QMessageBox::Warning, tr("告警"), "取流失败");
                     QTimer::singleShot(2500, box, SLOT(accept()));   // 1.5s弹框自动消失
                     box->exec();
                     delete  box;
                }
            }
        }
        av_free_packet(packet); //释放资源,否则内存会一直上升

        ///2017.8.7---lizhen
        msleep(2); //停一停  不然放的太快了
    }

    av_free(out_buffer);
    av_free(pFrameRGB);
    av_free(pFrame);
    avcodec_close(pCodecCtx);
    avformat_close_input(&pFormatCtx);

    pauseFlag = false;
    stopFlag = false;
    QMessageBox*  box = new   QMessageBox(QMessageBox::Warning, tr("告警"), "取流失败,结束取流");
    QTimer::singleShot(4500, box, SLOT(accept()));   // 1.5s弹框自动消失
    box->exec();
    delete box;
    qDebug() <<getCurrentTime()<< "rtsp  thread exit,ID: " << QThread::currentThreadId();
}

QString VideoPlayer::getCurrentTime()
{
    QDateTime datetime;
    //        qDebug() <<m_sysTimestr<<":系统时间更新测试\n";
    m_timeStr=datetime.currentDateTime().toString("HH:mm:ss");  //


   return m_timeStr;
}
