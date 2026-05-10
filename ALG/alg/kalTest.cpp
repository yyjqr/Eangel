#include <iostream>
//#include <Eigen/Dense>
#include <Eigen/Core>

using namespace Eigen;

VectorXd x(4);

// 使用卡尔曼滤波器进行预测
VectorXd predictNextPosition(double current_position, double current_velocity, double current_latitude, double current_yaw_angle) 
{
    // 更新步骤
    VectorXd z(2);
    z << current_position, current_latitude;

    // 预测步骤
    x = A * x;
    P = A * P * A.transpose() + Q;

    // 卡尔曼增益
    MatrixXd S = H * P * H.transpose() + R;
    MatrixXd K = P * H.transpose() * S.inverse();

    // 更新状态和协方差矩阵
    x = x + K * (z - H * x);
    P = (MatrixXd::Identity(4, 4) - K * H) * P;

    return x.head(2);
}

int main() {
    double current_position = 1.0;
    double current_velocity = 10.0;
    double current_latitude = 2.0;
    double current_yaw_angle = 0.5;
// 定义卡尔曼滤波器的参数
const double dt = 0.1;  // 时间间隔
const double noise_ax = 0.01;  // 加速度噪声的方差
const double noise_ay = 0.01;  // 加速度噪声的方差

// 定义状态转移矩阵
Eigen::MatrixXd A(4, 4);
A << 1, dt, 0, 0,
     0, 1, 0, 0,
     0, 0, 1, dt,
     0, 0, 0, 1;

// 定义观测矩阵
Eigen::MatrixXd H(2, 4);
H << 1, 0, 0, 0,
     0, 0, 1, 0;

// 定义状态噪声协方差矩阵
MatrixXd Q(4, 4);
Q << pow(dt, 4) / 4 * noise_ax, 0, pow(dt, 3) / 2 * noise_ax, 0,
     0, pow(dt, 2) * noise_ax, 0, pow(dt, 3) / 2 * noise_ax,
     pow(dt, 3) / 2 * noise_ay, 0, pow(dt, 2) / 4 * noise_ay, 0,
     0, pow(dt, 3) / 2 * noise_ay, 0, pow(dt, 2) * noise_ay;

// 定义观测噪声协方差矩阵
MatrixXd R(2, 2);
R << 0.1, 0,
     0, 0.1;

// 初始化卡尔曼滤波器的状态和协方差矩阵

x << initial_position, initial_velocity, initial_latitude, initial_yaw_angle;
MatrixXd P(4, 4);
P << 1, 0, 0, 0,
     0, 1, 0, 0,
     0, 0, 1, 0,
     0, 0, 0, 1;
     
    VectorXd predicted_position = predictNextPosition(current_position, current_velocity, current_latitude, current_yaw_angle);

    std::cout << "Predicted Next Position: (" << predicted_position(0) << ", " << predicted_position(1) << ")" << std::endl;

    return 0;
}
