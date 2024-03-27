import asyncio
import datetime
import json
import requests
import smtplib
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib3.exceptions import NewConnectionError

BASE_URL = 'http://localhost:5099/api/'

path_json = "configuration.json"
with open(path_json, 'r') as json_file:
    data = json.loads(json_file.read())

SERVICE_USER_EMAIL = data['PushUpAccountEmail']
SERVICE_USER_PASSWORD = data['PushUpAccountPassword']


async def send_email(email_to, message, subject):
    smtpObj = smtplib.SMTP('smtp.mail.ru', 587)
    smtpObj.starttls()
    smtpObj.login(SERVICE_USER_EMAIL, SERVICE_USER_PASSWORD)
    msg = MIMEMultipart()
    msg["From"] = SERVICE_USER_EMAIL
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))
    smtpObj.sendmail(SERVICE_USER_EMAIL, email_to, msg.as_string())
    smtpObj.quit()


async def get_token_jwt() -> str:
    try:
        response = requests.get(BASE_URL+'Token/signIn?email=' +
                                SERVICE_USER_EMAIL)
        return response.text
    except ConnectionRefusedError:
        print('Отсутствует подключение к серверу!')
    except NewConnectionError:
        print('Отсутствует подключение к серверу!')
    except ConnectionError:
        print('Отсутствует подключение к серверу!')


async def refresh_token_jwt(oldToken: str) -> str:
    try:
        response = requests.get(BASE_URL+'Token/refreshToken?oldToken=' +
                                oldToken)
        return response.text
    except ConnectionRefusedError:
        print('Отсутствует подключение к серверу!')
    except NewConnectionError:
        print('Отсутствует подключение к серверу!')
    except ConnectionError:
        print('Отсутствует подключение к серверу!')


async def check_date_tasks(jwtToken: str):
    try:
        headers = {
            'Authorization': f'Bearer {jwtToken}'
            }
        count_pushups = 0
        pushups = {}
        response_status_tasks = requests.get(BASE_URL+'StatusTasks', headers={
            'Authorization': f'Bearer {jwtToken}'
        })
        statustasks_list = []
        for statustask in response_status_tasks.json():
            if (statustask['nameStatusTask'] == 'Задана' or
                    statustask['nameStatusTask'] == 'Просрочена'):
                statustasks_list.append(statustask['idStatusTask'])
        response_tasks = requests.get(BASE_URL+'Tasks', headers=headers)
        for task in response_tasks.json():
            section_response = requests.get(BASE_URL+"Sections/" +
                                            task['sectionId'],
                                            headers=headers)
            section_data = section_response.json()
            executor_response = requests.get(BASE_URL+"Executors/gettask/" +
                                             task['idTask'],
                                             headers=headers)
            user_id = executor_response.json()['userExecutor']
            user_executor_response = requests.get(BASE_URL+"Users/" +
                                                  user_id,
                                                  headers=headers)
            user_executor_data = user_executor_response.json()
            current_date = datetime.datetime.now()
            convert_deadline_date_task = datetime.datetime.strptime(
                task['dateDeadlineTask'],
                '%Y-%m-%d'
            )
            if (current_date > convert_deadline_date_task and
               task['statusTaskId'] == statustasks_list[0]):
                json_data = {
                    'idTask': task['idTask'],
                    'bodyTask': task['bodyTask'],
                    'dateCreatingTask': task['dateCreatingTask'],
                    'timeCreatingTask': task['timeCreatingTask'],
                    'dateDeadlineTask': task['dateDeadlineTask'],
                    'timeDeadlineTask': task['timeDeadlineTask'],
                    'dateUploadDocument': task['dateUploadDocument'],
                    'timeUploadDocument': task['timeUploadDocument'],
                    'statusTaskId': statustasks_list[1],
                    'sectionId': task['sectionId']
                    }
                response_from_update = requests.put(BASE_URL+"Tasks/" +
                                                    task['idTask'],
                                                    json=json_data,
                                                    headers=headers)
                await send_email(user_executor_data['emailUser'],
                                 f"Здравствуйте, " +
                                 f"{user_executor_data['surnameUser']}" +
                                 f"{user_executor_data['nameUser']}!" +
                                 "Доводим до вашего сведения, что задание" +
                                 f"{section_data['nameSection']} " +
                                 "было просрочено!",
                                 "Уведомление о просроченности " +
                                 "срока выполнения" +
                                 f"задания {section_data['nameSection']}")
                count_pushups += 1
                pushups[count_pushups] = ('Было обнаружено просроченное' +
                                          ' задание! Уведомление выслано!')
            elif (current_date == convert_deadline_date_task and
                    task['statusTaskId'] == statustasks_list[0]):
                current_time = datetime.datetime.now().time()
                convert_deadline_time_task = datetime.datetime.strptime(
                    task['timeDeadlineTask'],
                    '%H:%M:%S'
                )
                if (current_time >= convert_deadline_time_task.time()):
                    json_data = {
                        'idTask': task['idTask'],
                        'bodyTask': task['bodyTask'],
                        'dateCreatingTask': task['dateCreatingTask'],
                        'timeCreatingTask': task['timeCreatingTask'],
                        'dateDeadlineTask': task['dateDeadlineTask'],
                        'timeDeadlineTask': task['timeDeadlineTask'],
                        'dateUploadDocument': task['dateUploadDocument'],
                        'timeUploadDocument': task['timeUploadDocument'],
                        'statusTaskId': statustasks_list[1],
                        'sectionId': task['sectionId']
                        }
                    id_task = task['idTask']
                    response_from_update = requests.put(BASE_URL +
                                                        "Tasks/" +
                                                        f"{id_task}",
                                                        json=json_data,
                                                        headers=headers)
                    await send_email(user_executor_data['emailUser'],
                                     f"Здравствуйте, " +
                                     f"{user_executor_data['surnameUser']}" +
                                     f"{user_executor_data['nameUser']}!" +
                                     f"Доводим до вашего сведения, " +
                                     "что задание " +
                                     f"{section_data['nameSection']}" +
                                     " было просрочено!",
                                     f"Уведомление о просроченности " +
                                     "срока выполнения " +
                                     f"задания {section_data['nameSection']}")
                    count_pushups += 1
                    pushups[count_pushups] = ('Было обнаружено просроченное' +
                                              ' задание! Уведомление выслано!')
            elif ((current_date -
                  timedelta(days=1)) == convert_deadline_date_task and
                  task['statusTaskId'] == statustasks_list[0]):
                await send_email(user_executor_data['emailUser'],
                                 f"Здравствуйте, " +
                                 f"{user_executor_data['surnameUser']}" +
                                 f" {user_executor_data['nameUser']}!" +
                                 "Напоминаем, что завтра истекает срок " +
                                 "сдачи задания " +
                                 f"{section_data['nameSection']}!",
                                 "Напоминание о окончании " +
                                 "срока выполнения " +
                                 f"задания {section_data['nameSection']}")
                count_pushups += 1
                pushups[count_pushups] = ('Было отправлено напоминание об' +
                                          'окончании срока выполнения ' +
                                          'задания!')
            elif ((current_date -
                  timedelta(days=5)) == convert_deadline_date_task and
                 task['statusTaskId'] == statustasks_list[0]):
                deadline = task['dateDeadlineTask']
                deadline_date = datetime.datetime.strptime(deadline,
                                                           '%d.%m.%Y')
                await send_email(user_executor_data['emailUser'],
                                 f"Здравствуйте, " +
                                 f"{user_executor_data['surnameUser']} " +
                                 f"{user_executor_data['nameUser']}! " +
                                 f"Напоминаем, что через 5 дней " +
                                 f"({deadline_date})" +
                                 f"истекает срок сдачи задания " +
                                 f"{section_data['nameSection']}!",
                                 f"Напоминание о окончании " +
                                 "срока выполнения " +
                                 f"задания {section_data['nameSection']}")
                count_pushups += 1
                pushups[count_pushups] = ('Было отправлено напоминание об ' +
                                          'окончании срока выполнения ' +
                                          'задания!')
            else:
                count_pushups += 1
                pushups[count_pushups] = ('Не было обнаружено ни ' +
                                          'просроченных заданий ' +
                                          'ни приближавшихся к ' +
                                          'окончанию срока ' +
                                          'выполнения заданий!')
        return pushups
    except ConnectionRefusedError:
        return {1: 'Отсутствует подключение к серверу!'}
    except ConnectionError:
        return {1: 'Отсутствует подключение к серверу!'}
    except NewConnectionError:
        return {1: 'Отсутствует подключение к серверу!'}


async def main():
    token_jwt = await get_token_jwt()
    while True:
        pushups = await check_date_tasks(token_jwt)
        for pushup in pushups:
            print(f'[{datetime.datetime.now().date()}' +
                  f'| {datetime.datetime.now().time()}]' +
                  f'- {pushups[pushup]}')
        await asyncio.sleep(600)
        token_jwt = await refresh_token_jwt(token_jwt)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Завершение работы программы...')
    except ConnectionRefusedError:
        print('Отсутствует подключение к серверу!')
    except ConnectionError:
        print('Отсутствует подключение к серверу!')
    except NewConnectionError:
        print('Отсутствует подключение к серверу!')
