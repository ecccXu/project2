"""
统一响应格式工具类
"""

def success_response(data=None, message="success", code=200):
    """
    成功响应
    :param data: 响应数据
    :param message: 响应消息
    :param code: 状态码
    :return: 标准化响应格式
    """
    if data is None:
        data = {}
    return {
        "code": code,
        "message": message,
        "data": data
    }


def error_response(message="Error occurred", code=400, data=None):
    """
    错误响应
    :param message: 错误消息
    :param code: 错误码
    :param data: 错误数据
    :return: 标准化错误响应格式
    """
    if data is None:
        data = {}
    return {
        "code": code,
        "message": message,
        "data": data
    }


def paginate_response(query, page=1, page_size=10, item_schema=None):
    """
    分页响应
    :param query: SQLAlchemy查询对象
    :param page: 页码
    :param page_size: 每页数量
    :param item_schema: 单个项目序列化函数
    :return: 分页响应格式
    """
    # 限制每页最大数量
    if page_size > 100:
        page_size = 100
    
    # 执行分页查询
    pagination = query.paginate(
        page=page, 
        per_page=page_size, 
        error_out=False
    )
    
    # 序列化数据
    if item_schema:
        items = [item_schema(item) for item in pagination.items]
    else:
        items = [item.to_dict() if hasattr(item, 'to_dict') else item.__dict__ for item in pagination.items]
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "total": pagination.total,
            "page": page,
            "pageSize": page_size,
            "items": items
        }
    }
