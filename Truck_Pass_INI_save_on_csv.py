import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon
from pyproj import Transformer

# 定义转换器，将 WGS 84 UTM Zone 50S 转换为 WGS 84
transformer = Transformer.from_crs("epsg:32750", "epsg:4326")

# 加载路口数据集
intersection_file_path = 'B4_intersections_unique_valid.csv'
intersection_data = pd.read_csv(intersection_file_path, header=None, names=["IntersectionID", "Coordinates"])

# 处理 Coordinates 列
intersection_data['Coordinates'] = intersection_data['Coordinates'].str.replace('LINESTRING\(', '', regex=True).str.replace('\)', '', regex=True)

# 定义一个函数，将坐标分割为单独的经度和纬度列表
def split_coordinates(coord_string):
    latitudes = []
    longitudes = []
    for coord in coord_string.split(','):
        try:
            lon, lat = map(float, coord.split())
            latitudes.append(lat)
            longitudes.append(lon)
        except ValueError:
            continue
    return latitudes, longitudes

# 应用函数以拆分坐标
intersection_data['Latitude'], intersection_data['Longitude'] = zip(*intersection_data['Coordinates'].apply(split_coordinates))

# 移除空的列表
intersection_data = intersection_data[intersection_data['Latitude'].map(len) > 0]

# 加载车辆移动数据集
truck_file_path = 'B4_truck_movements_01.csv'
truck_data = pd.read_csv(truck_file_path)

# 将车辆移动数据集中的坐标从 UTM 转换为经纬度
truck_data['Latitude'], truck_data['Longitude'] = transformer.transform(truck_data['X'].values, truck_data['Y'].values)

# 定义一个字典来存储每辆卡车通过的路口信息
truck_intersection_pass = {}

# 遍历每个路口
for intersection_id in intersection_data['IntersectionID'].unique():
    intersection_info = intersection_data[intersection_data['IntersectionID'] == intersection_id]
    if intersection_info.empty:
        continue

    # 创建路口的多边形
    polygon = Polygon(zip(intersection_info.iloc[0]['Longitude'], intersection_info.iloc[0]['Latitude']))

    # 检查每辆卡车是否通过该路口
    for truck_id in truck_data['Truck'].unique():
        truck_movements = truck_data[truck_data['Truck'] == truck_id]
        truck_path = [Point(lon, lat) for lon, lat in zip(truck_movements['Longitude'], truck_movements['Latitude'])]
        
        passed_through_intersection = any(polygon.contains(point) for point in truck_path)
        
        if passed_through_intersection:
            if truck_id not in truck_intersection_pass:
                truck_intersection_pass[truck_id] = []
            truck_intersection_pass[truck_id].append(intersection_id)

# 将结果写入CSV文件
output_data = {'Truck': [], 'IntersectionID': []}
for truck_id, intersections in truck_intersection_pass.items():
    for intersection_id in intersections:
        output_data['Truck'].append(truck_id)
        output_data['IntersectionID'].append(intersection_id)

output_df = pd.DataFrame(output_data)
output_df.to_csv('truck_intersection_pass.csv', index=False)

# 可视化函数
def plot_intersection_and_trucks(intersection_id):
    intersection_info = intersection_data[intersection_data['IntersectionID'] == intersection_id]
    if intersection_info.empty:
        print(f"No data found for Intersection ID: {intersection_id}")
        return

    plt.figure(figsize=(12, 8))

    # 绘制路口边界
    for i in range(len(intersection_info)):
        plt.plot(intersection_info.iloc[i]['Longitude'], intersection_info.iloc[i]['Latitude'], marker='o', label=f'{intersection_id} Boundary')

    # 创建路口的多边形
    polygon = Polygon(zip(intersection_info.iloc[0]['Longitude'], intersection_info.iloc[0]['Latitude']))

    # 绘制通过路口的车辆轨迹
    for truck_id in truck_data['Truck'].unique():
        truck_movements = truck_data[truck_data['Truck'] == truck_id]
        truck_path = [Point(lon, lat) for lon, lat in zip(truck_movements['Longitude'], truck_movements['Latitude'])]
        
        passed_through_intersection = []
        for point in truck_path:
            if polygon.contains(point):
                passed_through_intersection.append(point)
        
        if passed_through_intersection:
            lons = [point.x for point in passed_through_intersection]
            lats = [point.y for point in passed_through_intersection]
            plt.plot(lons, lats, marker='o', linestyle='-', label=f'Truck {truck_id}')

    plt.title(f'Intersection and Truck Movements Visualization: {intersection_id}')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.legend()
    plt.grid(True)
    plt.show()

# 示例：绘制特定路口的卡车轨迹
plot_intersection_and_trucks('INT_100')
