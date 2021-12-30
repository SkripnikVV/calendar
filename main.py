import argparse
import logging
import os
import re
from typing import List
from nsr.doc import NsrDoc

logger = logging.getLogger(__name__)
handler = logging.FileHandler(filename='calendar.log', mode='a')
logger.addHandler(handler)
logger.setLevel('INFO')
logging.basicConfig()


def load_nsr(file: str) -> NsrDoc:
    """загрузка документа нср"""
    with open(file, 'r', encoding='cp866') as fl:
        f = NsrDoc(fl.readlines())
    return f


def replace_links(lines: List[str], old_topic, new_topic: str):
    """заменяем ссылки из федерального эталона на новый топик"""

    count = 0
    pattern = f'(\x04)({old_topic})([\x04|\s|\.])'
    for index, line in enumerate(lines):
        if re.search(pattern, line):
            count += 1
            lines[index] = re.sub(pattern, '\g<1>' + new_topic + '\g<3>', line)
    logger.info(f'замена ссылки в строке:\t{count}\t{old_topic}\t{new_topic}')
    return lines


def make_new_head(old_head: List[str], new_topic: str) -> List[str]:
    """меняем команды в заголовке"""
    old_head = [line for line in old_head if line.find('!*LOG') == -1]
    old_head = [line for line in old_head if line.find('!STAGE') == -1]
    date_pattern = r'^([!DATE|!ACTIVE|!SORTDATE|!REVISION|!VINCLUDED]+)\s+\d\d/\d\d/(\d\d\d\d)'
    for index, line in enumerate(old_head):
        if re.search(r'^!TOPIC', line):
            old_head[index] = f'!TOPIC {new_topic}\n'
        elif re.search(r'^!NAME', line):
            rsm = re.search(r'(\d\d\d\d)(\s+год)', line)
            new_year = str(int(rsm[1]) + 1)
            old_head[index] = re.sub(r'(\d\d\d\d)(\s+год)', new_year + r'\g<2>', line)
            logger.info(f'set new NAME:\n{line}{old_head[index]}')
        elif re.search(date_pattern, line):
            rsm = re.search(date_pattern, line)
            new_year = str(int(rsm[2]) + 1)
            new_date = f'{rsm[1]} 01/01/{new_year}\n'
            old_head[index] = new_date
            logger.info(f'set new\n{rsm[1]}: {line}{new_date}')
    return old_head


def replace_first_header(etalon: List[str], doc: List[str]) -> List[str]:
    """Замена заголовка в эталоне"""

    def get_first_header(lines):
        for index, line in enumerate(lines):
            if line.strip() == '!STYLE #3':
                index += 1
                return index, lines[index]

    new_index, new_header = get_first_header(etalon)
    old_index, old_header = get_first_header(doc)
    logger.info(f'new_header\t{new_index}\t{new_header}')
    logger.info(f'old_header\t{old_index}\t{old_header}')
    rsm = re.search(r'\d\d\d\d', old_header)
    new_year = str(int(rsm[0]) + 1)
    old_header = old_header.replace(rsm[0], new_year)
    logger.info(f'patch year\t{old_index}\t{old_header}')
    etalon[new_index] = old_header
    return etalon


def replace_first_cmt(etalon: List[str], doc: List[str]) -> List[str]:
    """Замена первого комментария в эталоне"""

    def get_first_cmt(lines):
        for index, line in enumerate(lines):
            if line.strip() == '!STYLE J 1 72 1':
                index += 1
                return index, lines[index]

    new_index, new = get_first_cmt(etalon)
    old_index, old = get_first_cmt(doc)
    logger.info(f'new_cmt\t{new_index}\t{new}')
    logger.info(f'old_cmt\t{old_index}\t{old}')
    etalon[new_index] = old
    return etalon


def make_new_calendar(etalon: NsrDoc, calendar: NsrDoc, topic: str):
    """создаем новый налоговый календарь"""
    etalon.split()
    calendar.split()
    etalon_head_dict = etalon.header_to_dict()
    old_topic = etalon_head_dict.get('!TOPIC')[0]
    etalon.body = replace_links(etalon.body, old_topic, topic)
    return etalon, calendar

def path_service_info(calendar: NsrDoc) -> NsrDoc:
    """функция удаляет сервисинфо в старом календаре"""
    calendar.head = [line for line in calendar.head if line.find('!SERVICEINFO') == -1]
    return calendar


def save_nsr(data: NsrDoc, file: str):
    """сохранение документа в файл"""
    with open(file, 'w', encoding='cp866') as fl:
        fl.writelines(data.head)
        fl.writelines(data.body)


def get_args():
    """разбор аргументов"""
    parser = argparse.ArgumentParser(description='конвертация налоговых календарей')
    parser.add_argument('-nsr', type=str, dest='nsr', help='Прошлогодний НК')
    parser.add_argument('-etalon', type=str, dest='etalon', help='Эталон из НПП')
    parser.add_argument('-topic', type=str, dest='topic', help='Новый топик')
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    etalon = load_nsr(args.etalon)
    calendar = load_nsr(args.nsr)
    etalon, calendar = make_new_calendar(etalon, calendar, args.topic)
    new_head = make_new_head(calendar.head, args.topic)
    etalon.head = new_head
    etalon.body = replace_first_header(etalon.body, calendar.body)
    etalon.body = replace_first_cmt(etalon.body, calendar.body)
    calendar = path_service_info(calendar)
    if not os.path.exists('import'):
        os.makedirs('import')
    save_nsr(calendar, os.path.join('import', f'{args.nsr}'))
    save_nsr(etalon, os.path.join('import', f'{args.topic}.nsr'))
