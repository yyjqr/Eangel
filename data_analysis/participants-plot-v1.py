import dash
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time

# 获取文件路径
def get_input_path():
    default_path = os.getcwd()  # 获取当前工作路径
    user_input = input(f'请输入文件路径（直接回车使用当前路径: {default_path}）: ')

    if user_input.strip() == "":
        return default_path
    else:
        # 检查路径是否存在
        while not os.path.exists(user_input):
            print(f"路径不存在: {user_input}")
            user_input = input(f'请重新输入有效路径（直接回车使用当前路径: {default_path}）: ')
            if user_input.strip() == "":
                return default_path
        return user_input

# 获取文件路径
root_path = get_input_path()
print(f"使用的路径: {root_path}")
file_name = input('请输入csv文件名：') # '1719370800000.csv'
output_path = root_path
os.makedirs(output_path, exist_ok=True)

lr_file = os.path.join(root_path, file_name)
print(f"尝试读取文件: {lr_file}")

# 尝试读取CSV文件
try:
    # 检查文件是否存在
    if not os.path.exists(lr_file):
        raise FileNotFoundError(f"文件不存在: {lr_file}")
    
    # 尝试不同的分隔符
    try:
        #df = pd.read_csv(lr_file, sep='\t')
            # 尝试使用自动检测分隔符
        df = pd.read_csv(lr_file, sep=None, engine='python')
    except pd.errors.ParserError:
        print("制表符分隔失败，尝试逗号分隔")
        df = pd.read_csv(lr_file, sep=',')
    except Exception as e:
        print(f"读取CSV失败: {str(e)}")
        df = pd.read_csv(lr_file)  # 最后尝试自动检测分隔符
    
    print(f"成功读取文件，行数: {len(df)}")
    print("前5行数据:")
    print(df.head())
    # 打印列名以检查
    print("读取的列名:", df.columns.tolist())
    # 检查必要的列是否存在
    required_columns = ['ts', 'Lon', 'Lat', 'Vel', 'TargetID']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"CSV文件中缺少必要的列: {', '.join(missing_columns)}")
    
    print("数据列信息:")
    print(df.info())
    
except Exception as e:
    print(f"处理文件时出错: {str(e)}")
    print("程序将在5秒后退出...")
    time.sleep(5)
    exit()

# 数据处理
try:
    # 检查ts列是否为数值类型
    if df['ts'].dtype not in [np.int64, np.float64]:
        print("ts列不是数值类型，尝试转换...")
        df['ts'] = pd.to_numeric(df['ts'], errors='coerce')
        # 删除无效行
        df = df.dropna(subset=['ts'])
    
    df['datetime'] = pd.to_datetime(df['ts'], unit='s')
    df = df.sort_values('ts')
    
    print(f"时间范围: {df['datetime'].min()} 到 {df['datetime'].max()}")
    
    # 计算航向角（基于连续点之间的位置变化）
    def calculate_heading(group):
        group = group.sort_values('ts')
        lons = group['Lon'].values
        lats = group['Lat'].values

        headings = [0.0]  # 第一个点无航向
        for i in range(1, len(lons)):
            dlon = lons[i] - lons[i-1]
            dlat = lats[i] - lats[i-1]
            heading = np.degrees(np.arctan2(dlon, dlat)) % 360
            headings.append(heading)

        group['Heading'] = headings
        return group

    df = df.groupby('TargetID').apply(calculate_heading).reset_index(drop=True)
    
    print("航向角计算完成")
    print(f"目标ID列表: {df['TargetID'].unique()}")
    
except Exception as e:
    print(f"处理数据时出错: {str(e)}")
    print("程序将在5秒后退出...")
    time.sleep(5)
    exit()

# 创建Dash应用
try:
    app = dash.Dash(__name__)
    server = app.server
    
    # 添加调试信息面板
    debug_info = html.Div([
        html.H3("调试信息"),
        html.P(f"文件路径: {lr_file}"),
        html.P(f"数据行数: {len(df)}"),
        html.P(f"目标ID数量: {len(df['TargetID'].unique())}"),
        html.P(f"时间范围: {df['datetime'].min()} 到 {df['datetime'].max()}"),
        html.P(f"经度范围: {df['Lon'].min()} - {df['Lon'].max()}"),
        html.P(f"纬度范围: {df['Lat'].min()} - {df['Lat'].max()}"),
        html.P(f"速度范围: {df['Vel'].min()} - {df['Vel'].max()} m/s")
    ])
    
    app.layout = html.Div([
        html.H1(f"目标轨迹分析 (文件: {file_name})", style={'textAlign': 'center'}),
        
        debug_info,
        
        html.Div([
            dcc.Graph(id='trajectory-map', style={'width': '50%', 'display': 'inline-block'}),
            dcc.Graph(id='velocity-plot', style={'width': '50%', 'display': 'inline-block'})
        ]),

        html.Div([
            dcc.Graph(id='coordinate-time', style={'width': '50%', 'display': 'inline-block'}),
            dcc.Graph(id='heading-plot', style={'width': '50%', 'display': 'inline-block'})
        ]),

        html.Div([
            html.Label("轨迹点大小调整:"),
            dcc.Slider(
                id='marker-size',
                min=5,
                max=20,
                step=1,
                value=10,
                marks={i: str(i) for i in range(5, 21, 5)}
            )
        ], style={'width': '50%', 'margin': '20px auto'})
    ])
    
    print("Dash应用初始化完成")

except Exception as e:
    print(f"创建Dash应用时出错: {str(e)}")
    print("程序将在5秒后退出...")
    time.sleep(5)
    exit()

# 回调函数
@app.callback(
    [Output('trajectory-map', 'figure'),
     Output('velocity-plot', 'figure'),
     Output('coordinate-time', 'figure'),
     Output('heading-plot', 'figure')],
    [Input('marker-size', 'value')]
)
def update_plots(marker_size):
    try:
        # 轨迹地图
        fig_map = go.Figure()
        fig_map.add_trace(go.Scattermapbox(
            lon=df['Lon'],
            lat=df['Lat'],
            mode='lines+markers',
            marker=dict(size=marker_size, color=df['FrameID'], colorscale='Viridis'),
            text=[f"目标ID: {tid}<br>时间: {dt}<br>速度: {vel:.3f} m/s" 
                  for tid, dt, vel in zip(df['TargetID'], df['datetime'].dt.strftime('%H:%M:%S.%f'), df['Vel'])],
            hoverinfo='text',
            line=dict(color='blue', width=2)
        ))

        fig_map.update_layout(
            mapbox=dict(
                style='open-street-map',
                center=dict(lon=df['Lon'].mean(), lat=df['Lat'].mean()),
                zoom=18
            ),
            title='目标轨迹地图',
            margin={"r":0,"t":30,"l":0,"b":0}
        )

        # 速度图
        fig_vel = go.Figure()
        fig_vel.add_trace(go.Scatter(
            x=df['datetime'], y=df['Vel'],
            mode='lines+markers',
            line=dict(color='red', width=2),
            marker=dict(size=8),
            name='速度'
        ))
        fig_vel.update_layout(
            title='速度随时间变化',
            xaxis_title='时间',
            yaxis_title='速度 (m/s)',
            hovermode="x unified"
        )

        # 经纬度时间序列
        fig_coord = go.Figure()
        fig_coord.add_trace(go.Scatter(
            x=df['datetime'], y=df['Lon'],
            mode='lines+markers', name='经度',
            line=dict(color='blue')))
        fig_coord.add_trace(go.Scatter(
            x=df['datetime'], y=df['Lat'],
            mode='lines+markers', name='纬度',
            line=dict(color='green')))
        fig_coord.update_layout(
            title='经纬度随时间变化',
            yaxis_title='坐标值',
            xaxis_title='时间',
            legend_title='坐标类型'
        )

        # 航向角图
        fig_heading = go.Figure()
        fig_heading.add_trace(go.Scatter(
            x=df['datetime'], y=df['Heading'],
            mode='lines+markers',
            line=dict(color='purple', width=2),
            marker=dict(size=8),
            name='航向角'
        ))
        fig_heading.update_layout(
            title='航向角随时间变化',
            xaxis_title='时间',
            yaxis_title='航向角 (度)',
            yaxis=dict(range=[0, 360])
        )

        return fig_map, fig_vel, fig_coord, fig_heading
    
    except Exception as e:
        print(f"更新图表时出错: {str(e)}")
        # 返回空图表
        empty_fig = go.Figure()
        empty_fig.update_layout(title="图表加载失败", annotations=[
            dict(text="图表加载失败", showarrow=False, font=dict(size=20))
        ])
        return empty_fig, empty_fig, empty_fig, empty_fig

if __name__ == '__main__':
    try:
        print("启动Dash服务器...")
        print("如果无法访问，请尝试以下步骤:")
        print("1. 检查防火墙设置，确保8050端口已开放")
        print("2. 尝试使用 http://localhost:8050 访问")
        print("3. 如果使用服务器，请确保绑定到正确IP地址")
        print("4. 检查是否有其他程序占用了8050端口")
        
        # 添加更多调试信息
        print("\n服务器启动信息:")
        app.run_server(debug=True, host='0.0.0.0', port=8050)
        
    except Exception as e:
        print(f"启动服务器时出错: {str(e)}")
        print("程序将在5秒后退出...")
        time.sleep(5)
