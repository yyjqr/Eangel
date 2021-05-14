/** @brief moving robot control, using cam
 *  @date 2020.12
 * @author Jack
 * @addr  yyjqr789@sina.com
 */
#include "mainwindow.h"
#include <QApplication>
#include "logging.h"
#include <QDateTime>
#include <QTextCodec>   //中文支持
#include <QDir>

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    QDateTime datetime;
    Log camlog;
    QTextCodec::setCodecForLocale(QTextCodec::codecForName("UTF-8")); //中文字符支持
    QString timestr=datetime.currentDateTime().toString("yyyyMMdd_HHmmss");  //yyyyMMdd_HHmmss-->MMdd_HHmmss
    std::string log_file="./log/";   //日志在打开cam之前创建。
    std::string log_path=".\\log";
    string command;
    QDir q_dir;
    q_dir.setPath(QString::fromStdString(log_path));
    if(!q_dir.exists())
    {
        command = "mkdir" + log_path;
        system(command.c_str());
    }
    else{
        cout<<"日志路径存在\n";
    }
    log_file+=timestr.toStdString();
    log_file+=".log";
    camlog.SetFile(log_file.c_str());
    MainWindow w;
    w.show();
    w.setWindowTitle(QString::fromLocal8Bit("移动机器人交互控制软件_v1.0.0"));
    return a.exec();
}
