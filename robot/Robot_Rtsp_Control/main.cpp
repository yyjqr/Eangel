/** @brief moving robot control, using cam and RTSP 。
 *  传输不同分辨率的摄像头图像，并显示
 *  基于qt5和qt6相关接口变化，重新调整相关写法，如去掉endl;
 *  @date 2022.01-
 *  @date 2022.10-2023完善
 *  @date  2024.04 基于qt6，qt5相关接口调整部分写法
 * @author Jack
 * @addr  yyjqr789@sina.com
 */


#include <QApplication>
#include <QTextcodec>
#include <QDateTime>
#include <qdir.h>
#include <string>
#include "logging.h"
#include "mainwindow.h"
using std::string;

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    QTextCodec *codec = QTextCodec::codecForName("UTF-8");  //中文字符支持
    QTextCodec::setCodecForLocale(codec);

    QDateTime datetime;
    Log camlog;

    QString timestr=datetime.currentDateTime().toString("yyyyMMdd_HHmmss");  //
    string log_path=".\\robotLog"; //日志在打开之前创建,相对路径。
    std::string log_file="./robotLog/";   //日志在打开cam之前创建。
    QDir q_dir;
    string command;
    q_dir.setPath(QString::fromStdString(log_path));
    if(!q_dir.exists())
    {
        command = "mkdir " + log_path;
        system(command.c_str());
    }
    log_file+=timestr.toStdString();
    log_file+=".log";
    camlog.SetFile(log_file.c_str());
    MainWindow w;
    w.show();
    // 将QString转换为字节数组
    QString originalString = "机器人交互控制—v1.2";
    QByteArray byteArray = codec->fromUnicode(originalString);

    // 将字节数组转换为QString
    QString convertedString = codec->toUnicode(byteArray);

    w.setWindowTitle(convertedString); //
    return a.exec();
}
