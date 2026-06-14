# -*- coding: utf-8 -*-
"""
读取大连商品交易所接口说明文档，提取接口信息并保存为JSON

核心策略：
1. 按顺序遍历所有元素，维护当前接口上下文
2. 对于每个表格，根据其前后段落的内容确定其用途
3. 表格匹配规则：
   - 前一个元素是"请求Header参数"文本 -> header表格
   - 前一个元素是"请求Body参数"文本 -> body表格
   - 前一个元素是"响应示例"文本 -> response表格
"""

import json
from pathlib import Path
from docx import Document


def get_document_elements(doc):
    """获取文档中的所有元素（段落和表格），按顺序返回"""
    elements = []
    body = doc.element.body
    NS = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

    for child in body:
        tag_local = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag_local == 'p':
            text = ''
            style = None
            for t in child.iter('%st' % NS):
                if t.text:
                    text += t.text
            pPr = child.find('%spPr' % NS)
            if pPr is not None:
                pStyle = pPr.find('%spStyle' % NS)
                if pStyle is not None:
                    style = pStyle.get('%sval' % NS)
            elements.append(('paragraph', {'text': text.strip(), 'style': style}))
        elif tag_local == 'tbl':
            table_data = []
            for row in child.iter('%str' % NS):
                row_data = []
                for cell in row.iter('%stc' % NS):
                    cell_text = ''
                    for t in cell.iter('%st' % NS):
                        if t.text:
                            cell_text += t.text
                    row_data.append(cell_text.strip())
                table_data.append(row_data)
            elements.append(('table', table_data))

    return elements


def parse_table(table):
    """解析表格，返回参数列表"""
    if not table or not table[0]:
        return []

    header = table[0]
    params = []

    # 判断表格类型
    has_param_name = '参数名' in header
    has_success = 'success' in header or 'code' in header
    has_status_code = '状态码' in header and '说明' in header

    for row in table[1:]:
        if has_param_name and len(row) >= 2:
            # 参数表格
            param = {
                'name': row[0] if len(row) > 0 else '',
                'description': row[1] if len(row) > 1 else ''
            }
            if len(row) >= 5:
                param['example'] = row[1]
                param['type'] = row[2]
                param['required'] = row[3]
                param['description'] = row[4]
            params.append(param)
        elif has_success or has_status_code:
            # 响应/状态码表格
            if len(row) >= 2:
                params.append({
                    'field': row[0],
                    'description': row[1]
                })

    return params


def parse_document(doc):
    """解析文档，提取接口信息"""
    elements = get_document_elements(doc)

    interfaces = []
    current_interface = None
    current_section = None
    next_table_type = None  # 'header', 'body', 'response'

    for idx, (elem_type, data) in enumerate(elements):
        prev_text = ''
        if idx > 0:
            if elements[idx-1][0] == 'paragraph':
                prev_text = elements[idx-1][1]['text']

        if elem_type == 'paragraph':
            text = data['text']
            style = data['style']

            if not text:
                continue

            # 一级标题 -> 大章节
            if style == '2':
                if current_interface:
                    interfaces.append(current_interface)
                    current_interface = None

                if text not in ['全局公共参数', '状态码说明']:
                    current_section = text
                next_table_type = None

            # 二级标题 -> 具体接口
            elif style == '4':
                if current_interface:
                    interfaces.append(current_interface)

                current_interface = {
                    'section': current_section,
                    'name': text,
                    'url': '',
                    'method': '',
                    'header_params': [],
                    'body_params': [],
                    'response': [],
                    'raw_tables': []  # 保留原始表格用于调试
                }
                next_table_type = None

            # 接口详情处理
            elif current_interface:
                if text.startswith('http'):
                    current_interface['url'] = text
                elif 'POST' in text or 'GET' in text:
                    current_interface['method'] = text
                elif '请求Header参数' in text:
                    next_table_type = 'header'
                elif '请求Body参数' in text:
                    next_table_type = 'body'
                elif '响应示例' in text:
                    next_table_type = 'response'

        elif elem_type == 'table' and current_interface:
            table = data
            header = table[0] if table else []

            # 解析表格
            params = parse_table(table)

            if params:
                # 根据表格内容和上下文决定放到哪里
                # 优先级：1. 表格数据判断(响应表格特征) 2. 表头判断 3. next_table_type

                table_type = None

                # 首先检查是否是响应表格（根据数据内容判断）
                # 响应表格的特征：包含 success, code, msg, error, data 等字段
                response_fields = {'success', 'code', 'msg', 'error', 'data', 'total', 'page', 'rows', 'list', 'result'}
                first_names = [p.get('name', '').lower() for p in params[:3]]
                if any(f in first_names for f in response_fields):
                    table_type = 'response'
                # 其次根据表头判断
                elif 'success' in header or 'code' in header:
                    table_type = 'response'
                elif '参数名' in header:
                    # 有参数名的表格
                    if '是否必填' in header:
                        # 有是否必填 -> header或body参数
                        table_type = next_table_type if next_table_type in ('header', 'body') else 'header'
                    else:
                        # 没有是否必填 -> body参数
                        table_type = next_table_type if next_table_type == 'body' else 'body'

                # 如果根据内容判断不了，用next_table_type
                if not table_type:
                    table_type = next_table_type

                # 兜底：默认当body处理
                if not table_type:
                    table_type = 'body'

                # 存储参数
                if table_type == 'header':
                    current_interface['header_params'].extend(params)
                elif table_type == 'body':
                    current_interface['body_params'].extend(params)
                elif table_type == 'response':
                    current_interface['response'].extend(params)
                else:
                    current_interface['body_params'].extend(params)

                current_interface['raw_tables'].append({
                    'type': table_type,
                    'header': header,
                    'params': params
                })

            next_table_type = None

    if current_interface:
        interfaces.append(current_interface)

    return {
        'interfaces': interfaces,
        'total_count': len(interfaces)
    }


def main():
    doc_path = Path(__file__).parent.parent / 'docs' / '大连商品交易所接口说明.docx'
    output_path = Path(__file__).parent.parent / 'docs' / 'dce_interfaces.json'

    print(f"读取文档: {doc_path}")

    doc = Document(doc_path)
    elements = get_document_elements(doc)
    print(f"文档元素数量: {len(elements)}")

    result = parse_document(doc)

    print(f"\n解析到 {result['total_count']} 个接口")

    for i, iface in enumerate(result['interfaces']):
        print(f"\n{i+1}. [{iface['section']}] {iface['name']}")
        print(f"   URL: {iface['url']}")
        print(f"   Method: {iface['method']}")
        print(f"   Header参数: {len(iface['header_params'])} 个")
        print(f"   Body参数: {len(iface['body_params'])} 个")
        print(f"   响应字段: {len(iface['response'])} 个")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: {output_path}")


if __name__ == '__main__':
    main()