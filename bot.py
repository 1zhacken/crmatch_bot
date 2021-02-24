# -*- coding: utf-8 -*-
import telebot
import json
from datetime import datetime
import time as timelib

#инициализация бота
session = {} #тут временно храним данные о анкете на время создания

#глобальные константы
bot = telebot.TeleBot('') #token
_match_channel = '@creatorsmatching'
_music_channel = '@pesennyk'
_admin = 401967130 #айди чата с админом

#красивое время
def time():
    return f'[{datetime.now().strftime("%H:%M:%S")}] '

#восстанавливаем бд
db = open('db') #файл базы данных лайков для восстановления
s = db.read() #читаем содержимое файла
_songs = json.loads(s) or {} #если получилось прочитать, то загружаем. если нет - обнуляем
print(time() + str(_songs).replace('},', '},\n')) #показываем че там внутри
db.close() #закрываем файлы базы

#экспорт в бд
def save():
    db = open('db', 'w')
    db.write(json.dumps(_songs))
    db.close()

#метод создания клавиатуры с лайками
def generate_keyboard(count=0):
    markup = telebot.types.InlineKeyboardMarkup()
    like_btn = telebot.types.InlineKeyboardButton(f"👍 {str(count)}", callback_data='like')
    markup.add(like_btn)
    return markup

#получение лайкнувших по песне
@bot.message_handler(commands=['stat234'])
def stat(msg):
    if msg.chat.type != "private":
        return
    bot.reply_to(msg, 'waiting for audiofile')
    bot.register_next_step_handler(msg, get_file)

def get_file(msg):
    if msg.audio.file_unique_id in _songs: #если песня с этим айди есть в бд
        for u in _songs[msg.audio.file_unique_id]['users']: #проходимся по массиву лайкнувших
            bot.reply_to(msg, f'[{msg.audio.file_unique_id}](tg://user?id={u})', parse_mode="Markdown") #откидываем ссылки на них
            timelib.sleep(0.5) #с паузой
        return
    bot.reply_to(msg, 'Этой песни нет в базе') #сработает только если песни нет в бд

#отправка песни в песенник
@bot.message_handler(commands=['send_song'])
def send_song(msg):
    #проверка на говно из общих чатов
    if msg.chat.type != "private":
        bot.reply_to(msg, 'Я не работаю в чатах... Напиши в личку')
        return

    bot.send_message(msg.chat.id, 'Отправь следующим сообщением файл со своей песней. Это может быть mp3-файл, ссылка на ютуб или другие платформы. Но знай, что все песни проходят модерацию.')
    bot.register_next_step_handler(msg, forward_song)

def forward_song(msg):
    if msg.audio == None: #если прислали говно без музыки
        bot.send_message(msg.chat.id, 'Мне нужен файл с музыкой.')
        bot.send_message(_admin, msg.text + ' [prislal](tg://user?id='+str(msg.from_user.id)+')', parse_mode='Markdown') #сообщаем о петухе
        welcome(msg) #возвращаем на старт
        return

    #если все ок
    _songs[msg.audio.file_unique_id] = {'likes': 0, 'users': []} #добавляем песню в список песен
    bot.send_audio(_music_channel, msg.audio.file_id, reply_markup=generate_keyboard(_songs[msg.audio.file_unique_id]['likes'])) #высылаем в канал
    bot.send_audio(_admin, msg.audio.file_id, caption='[prislal](tg://user?id={})'.format(msg.from_user.id), parse_mode='Markdown') #в личку с ссылкой на аккаунт
    bot.send_audio('@kievsound', msg.audio.file_id, caption='Кто-то прислал новую песню! Скорее послушай и оцени! t.me/pesennyk') #в общий чат
    bot.reply_to(msg, 'Звучит круто! Уверен, твоя песня соберет много лайков!') #подлизываем автору
    print(time() + f'new song: {msg.audio.file_unique_id}')
    save() #сохраняем бд

#тут ловим нажатие на кнопочку
@bot.callback_query_handler(func=lambda query: True)
def callback_query(query):
    if query.data == "like": #проверяем что за кнопку нажали
        if query.from_user.id not in _songs[query.message.audio.file_unique_id]['users']: #если юзер еще не лайкал эту песню
            _songs[query.message.audio.file_unique_id]['likes'] += 1 #инкремент лайков
            _songs[query.message.audio.file_unique_id]['users'].append(query.from_user.id) #сохраним его в список шиндлера
        else: #если лайкал
            _songs[query.message.audio.file_unique_id]['likes'] -= 1 #лайк удалим
            _songs[query.message.audio.file_unique_id]['users'].remove(query.from_user.id) #из списка вычеркнем
        
        bot.answer_callback_query(query.id, "Твой голос учтен") #кинем ответ на колбек
        save() #сохраним бд
        bot.edit_message_reply_markup(query.message.chat.id, #обновим кнопку
                                    query.message.message_id, 
                                    reply_markup=generate_keyboard(count=_songs[query.message.audio.file_unique_id]['likes']))

#здороваемся
@bot.message_handler(commands=['start'])
def welcome(msg):
    if msg.chat.type != "private":
        bot.reply_to(msg, 'Я не работаю в чатах... Напиши в личку')
        return

    markup = telebot.types.ReplyKeyboardRemove(selective=False)
    bot.send_message(msg.chat.id,
'''Привет! Вот что ты можешь сделать:
1. Отправить свою анкету для поиска группы - /create
2. Отправить свою музыку в наш канал - /send_song''', reply_markup=markup)

@bot.message_handler(commands=['remove'])
def remove_keyboard(msg):
    markup = telebot.types.ReplyKeyboardRemove(selective=False)
    bot.reply_to(msg, 'trying remove keyboard', reply_markup=markup)

#регистрация в канал с анкетами
@bot.message_handler(commands=['create'])
def create(msg):
    #проверка на говно из общего чата
    if msg.chat.type != "private":
        bot.reply_to(msg, 'Я не работаю в чатах... Напиши в личку')
        return

    markup = telebot.types.ReplyKeyboardRemove(selective=False)
    bot.send_message(msg.chat.id,
'''Привет! Давай найдем группу для тебя :)
Я задам пару вопросов чтобы сформировать твою анкету музыканта''', reply_markup=markup)
    session[msg.from_user.id] = {} #создаем в сессии запись для текущего юзера
    m = bot.reply_to(msg, 'Первый вопрос: как тебя зовут?')

    bot.register_next_step_handler(m, name)

def name(msg):
    #если вдруг вызвали новую команду
    if msg.text == '/send_song':
        send_song(msg)
        return

    session[msg.from_user.id]['name'] = msg.text  #записываем инфу
    m = bot.reply_to(msg, 'Ок! Теперь скажи сколько тебе лет')

    bot.register_next_step_handler(m, age)

def age(msg):
    if msg.text == '/send_song':
        send_song(msg)
        return

    session[msg.from_user.id]['age'] = msg.text #записываем инфу
    m = bot.reply_to(msg, 'Запомнил. На каком инструменте ты играешь?')

    bot.register_next_step_handler(m, gear)

def gear(msg):
    if msg.text == '/send_song':
        send_song(msg)
        return

    session[msg.from_user.id]['gear'] = msg.text #записываем инфу
    m = bot.reply_to(msg, 'Есть! Теперь напиши жанр музыки, в котором ты хочешь работать (можно несколько через запятую)')

    bot.register_next_step_handler(m, genre)

def genre(msg):
    if msg.text == '/send_song':
        send_song(msg)
        return

    session[msg.from_user.id]['genre'] = msg.text #записываем инфу
    m = bot.reply_to(msg, 'Интересно, интересно. А какие группы тебя вдохновляют? (Можно несколько через запятую)')

    bot.register_next_step_handler(m, groups)

def groups(msg):
    if msg.text == '/send_song':
        send_song(msg)
        return

    session[msg.from_user.id]['groups'] = msg.text #записываем инфу
    m = bot.reply_to(msg, 'Хороший вкус! Какие у тебя требования к другим участникам группы?')

    bot.register_next_step_handler(m, bandmates)

def bandmates(msg):
    if msg.text == '/send_song':
        send_song(msg)
        return

    session[msg.from_user.id]['bandmates'] = msg.text #записываем инфу
    #формируем анкету
    session[msg.from_user.id]['data'] = ''' 
{}, {}
**Играю на:** {}
**Хочу писать:** {}
**Вдохновляют:** {}
**От тебя требуется:** {}

[Связаться](tg://user?id={})'''.format(session[msg.from_user.id]['name'],
                                        session[msg.from_user.id]['age'],
                                        session[msg.from_user.id]['gear'],
                                        session[msg.from_user.id]['genre'],
                                        session[msg.from_user.id]['groups'],
                                        session[msg.from_user.id]['bandmates'],
                                        msg.from_user.id)

    #делаем клавиатурку
    reply = telebot.types.ReplyKeyboardMarkup(True, one_time_keyboard=True)
    reply.row('Да, постим', 'Нет, заполняем заново')

    bot.reply_to(msg, 'Все готово! Проверяй, все ли правильно?')
    #отправляем с клавиатуркой
    m = bot.send_message(msg.chat.id, str(session[msg.from_user.id]['data']), parse_mode="Markdown", reply_markup=reply)
    
    bot.register_next_step_handler(m, complete)

def complete(msg):
    if msg.text == '/send_song':
        send_song(msg)
        return
    
    #если нажата кнопка Да
    if 'Да' in msg.text:
        bot.send_message(_match_channel, session[msg.from_user.id]['data'], parse_mode="Markdown")

        markup = telebot.types.ReplyKeyboardRemove(selective=False)
        bot.send_message(msg.chat.id, "Готово!", reply_markup=markup) #чистим клавиатуру
        session.pop(msg.from_user.id) #удаляем запись из сессии
        print(time() + f'new user: {msg.from_user.id}')

    else:
        welcome(msg) #на старт

#запуск бота
def start():
    try:
        bot.polling()
    except KeyboardInterrupt: #нажали контрол ц
        return #вышли из программы
    except Exception as e: #отлавливаем сбой
        bot.send_message(_admin, 'Ooops... [{}]'.format(e)) #дергаем админа
        start() #продолжаем работать

start()
