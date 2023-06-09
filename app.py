from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL, MySQLdb
import pymysql
import bcrypt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from time import sleep

import os
import pathlib
from flask import Flask, url_for, redirect,  render_template, request
from flask import jsonify
import logging

logging.basicConfig(filename='error.log', level=logging.DEBUG)



app = Flask(__name__)
app.secret_key = "abc123"

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12345678'
app.config['MYSQL_DB'] = 'secondhand_bookweb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)


# 取得目前檔案所在的資料夾 
SRC_PATH =  pathlib.Path(__file__).parent.absolute()
# 結合目前的檔案路徑和static及uploads路徑，取得儲存書籍照片資料夾(uploads)的位置
UPLOAD_FOLDER = os.path.join(SRC_PATH,  'static', 'uploads')
print(UPLOAD_FOLDER)

#最初的模板
"""
@app.route('/')
def hello_world():
    return 'Hello World! 上架: /book_create    修改書籍資訊: /book_update/(+B_BookID)    書籍列表: /book_display    搜尋書籍: /book_search/(+search_str)'
"""

# 首頁
@app.route('/')
def index():
    try:
        return render_template("new_index.html")
    except Exception as e:
        logging.exception("Error occurred during index")
        return "An error occurred during index. Please check the error log for more information.", 500

#註冊功能實現，需要pip install bcrypt
@app.route('/register', methods=["GET", "POST"]) 
def register():
    try: 
        if request.method == 'GET':
            return render_template("register.html")
        else:
            A_Email = request.form['A_Email']
            A_Password = request.form['A_Password']
            A_StuID = request.form['A_StuID']
            A_BirthDate = request.form['A_BirthDate']
            A_Major = request.form['A_Major']

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO account_manage (A_Email, A_Password, A_StuID, A_BirthDate, A_Major) VALUES (%s,%s,%s,%s,%s,%s)",(A_Email,A_Password,A_StuID,A_BirthDate,A_Major))
            mysql.connection.commit()
            session['A_StuID'] = request.form['A_StuID']
            session['A_Email'] = request.form['A_Email']
            return redirect(url_for('index'))
    except Exception as e:
        logging.exception("Error occurred during registration")
        return "An error occurred during registration. Please check the error log for more information.", 500
    
#登入功能實現，加上MySQL和Mysqldb
@app.route('/login',methods=["GET","POST"])
def login():
    print("Entering login function")
    try:
        if request.method == "POST":
            print("Handling POST request")
            A_StuID = request.form['A_StuID']
            A_Password = request.form['A_Password']
            
            print(f"Login attempt: A_StuID={A_StuID}, A_Password={A_Password}")

            curl = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            curl.execute("SELECT * FROM account_manage WHERE A_StuID=%s",(A_StuID,))
            user = curl.fetchone()
            curl.close()
            
            print(f"User fetched from database: {user}")

            if len(user) > 0:
                if A_Password == user["A_Password"]:
                    session['A_StuID'] = user['A_StuID']
                    session['A_Email'] = user['A_Email']
                    return render_template("new_index.html")
                else:
                    return "Error password and email not match"
            else:
                return "Error user not found"
        else:
            print("Handling GET request")
            return render_template("login.html")
    except Exception as e:
        logging.exception("Error occurred during login")
        print(e)
        return "An error occurred during login. Please check the error log for more information.", 500

#將session清除，登出功能
@app.route('/logout')
def logout():
    session.clear()
    return render_template("new_index.html")
    
# 連接mysql
def get_conn():
    return pymysql.connect(
        host = '127.0.0.1', 
        user = 'root', 
        password = '12345678', 
        database = 'secondhand_bookweb', 
        charset = 'utf8'
    )

# 新增資料
def insert_or_update_data(sql):
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            conn.commit()
        finally:
            conn.close()

# 顯示[用戶資訊]頁面
@app.route('/user_information')
def show_user_information():
    A_StuID = session.get('A_StuID')
    sql = "select * from account_manage where A_StuID = '{}'".format(A_StuID)
    conn = get_conn()

    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        datas = cursor.fetchall()
        account = datas[0]

        # 獲取買家評價
        buyer_sql = "SELECT O_SalerRating FROM order_information WHERE A_BuyerID = '{}' AND O_SalerRating > 0".format(A_StuID)
        cursor.execute(buyer_sql)
        buyer_ratings = [item['O_SalerRating'] for item in cursor.fetchall()]

        # 獲取賣家評價
        seller_sql = "SELECT O_BuyerRating FROM order_information WHERE B_SalerID = '{}' AND O_BuyerRating > 0".format(A_StuID)
        cursor.execute(seller_sql)
        seller_ratings = [item['O_BuyerRating'] for item in cursor.fetchall()]

        # 合併買家和賣家評價
        all_ratings = buyer_ratings + seller_ratings

        # 如果存在評價，則計算平均值並四捨五入
        total_avg_rating = round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else 0

        # 更新A_CreditPoint值
        update_sql = "UPDATE account_manage SET A_CreditPoint = {} WHERE A_StuID = '{}'".format(total_avg_rating, A_StuID)
        cursor.execute(update_sql)
        conn.commit()

    finally:
        conn.close()
    print(sql)
    return render_template("user_information.html", account=account, A_StuID=A_StuID)



# 個人資料頁面
@app.route('/user_information_profile')
def show_user_information_profile():
    A_StuID = session.get('A_StuID')
    sql = "select * from account_manage where A_StuID = '{}'".format(A_StuID) #怎麼取A_StuID的值
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        datas = cursor.fetchall()
        account = datas[0]
    finally:
        conn.close()
    print(sql)
    return render_template("user_information_profile.html", account=account)

# [修改個人資料] 顯示網站
@app.route('/user_information_profile_update/<A_StuID>')
def show_user_information_profile_update(A_StuID):
    A_StuID = session.get('A_StuID')
    sql = "select * from account_manage where A_StuID = '{}'".format(A_StuID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        datas = cursor.fetchall()
        account = datas[0]
    finally:
        conn.close()
    print(sql)
    message = "User information updated successfully!"
#    return render_template("user_information_profile_update.html", account=account)
    return render_template("user_information_profile_update.html", account=account, message=message)

# [修改個人資料] 接收表單提交的數據 
@app.route('/do_user_information_profile_update', methods=["GET","POST"])
def user_information_profile_update():
    # 儲存頭像
    file = request.files['A_image']
    if file.filename != '':
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        print('--new profile picture:' + file.filename)
        A_image = file.filename
    else:
        A_image = ''  # 沒有上傳新圖像則設A_image為空字串供下面程式碼判斷

    # 判斷密碼
    A_Password_old = request.form.get("A_Password_old") #為判斷舊密碼是否正確
    A_Password_new = request.form.get("A_Password_new")
    file = request.files['A_image']
    if A_Password_old != '' and A_Password_new != '':
        A_Password = A_Password_new
        print('--new password')
    else:
        A_Password = ''  # 沒有輸入舊密碼&新密碼則設A_Password為空字串供下面程式碼判斷

    print(request.form)
    A_StuID = request.form.get("A_StuID")
    A_Email = request.form.get("A_Email")
    A_StuID = request.form.get("A_StuID")
    A_BirthDate = request.form.get("A_BirthDate")
    A_Major = request.form.get("A_Major")
    A_Nickname = request.form.get("A_Nickname")

    try:
        sql = f'''
        update account_manage set A_Email='{A_Email}', 
        A_BirthDate='{A_BirthDate}', A_Major='{A_Major}', A_Nickname='{A_Nickname}'
        '''
        if A_image != '': 
            sql += f", A_image='{A_image}'"  #有傳新圖片才更新這欄SQL

        if A_Password != '': 
            sql += f", A_Password='{A_Password}' where A_StuID='{A_StuID}' and A_Password='{A_Password_old}'"  #有更改密碼才更新這欄SQL並檢查舊密碼是否正確
        else:
            sql += f" where A_StuID='{A_StuID}'"

        print(sql)
        insert_or_update_data(sql)

#        redirect(url_for("show_user_information_profile")) #trying:重新導向並用彈出式視窗顯示成功訊息

#        return "User information updated successfully!" # 舊密碼錯誤不會更新資訊，但還是顯示成功訊息
        return redirect(url_for("show_user_information")) #trying:重新導向並用彈出式視窗顯示成功訊息

    
    except Exception as e:
        logging.exception("Error occurred during updating user information")
        print(e)
        return "An error occurred during updating user information. Please check the error log for more information.", 500

# 顯示[賣家介面] 篩選條件：B_SalerID、B_SaleStatus
@app.route('/user_information_sellerpage')
def show_user_information_sellerpage():
    B_SalerID = session.get('A_StuID')
    ###
    # 已上架(B_SaleStatus='賣家已上架')
    sql_uploaded = '''
    select B_BookID, B_BookName, B_BookPic, B_SaleStatus from book_information 
    where B_SalerID='{}' and B_SaleStatus='賣家已上架'
    '''.format(B_SalerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_uploaded)
        datas_uploaded = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_uploaded)

    # 已上架(B_SaleStatus='賣家已上架')
    sql_uploaded = '''
    select B_BookID, B_BookName, B_BookPic, B_SaleStatus from book_information 
    where B_SalerID='{}' and B_SaleStatus='賣家已上架'
    '''.format(B_SalerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_uploaded)
        datas_uploaded = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_uploaded)

    # 進行中(B_SaleStatus='買家已下單' or '賣家已確認' or '賣家已出貨')，包含買家資訊
    sql_processing = '''
    select o.B_BookID, b.B_BookName, b.B_BookPic, b.B_SaleStatus, 
    o.A_BuyerID, a.A_Nickname, a.A_CreditPoint, a.A_TradeCount, a.A_ViolationCount
    from book_information b, order_information o, account_manage a 
    where b.B_BookID = o.B_BookID and o.A_BuyerID = a.A_StuID 
    and o.B_SalerID='{}' and b.B_SaleStatus in ('買家已下單', '賣家已確認', '賣家已出貨')
    '''.format(B_SalerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_processing)
        datas_processing = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_processing)

    # 已完成(B_SaleStatus='訂單已完成')
    sql_finished = '''
    select b.B_BookID, b.B_BookName, b.B_BookPic, b.B_SaleStatus, o.O_SalerRating, o.O_BuyerRating from book_information b, order_information o 
    where b.B_SalerID='{}' and b.B_BookID=o.B_BookID and B_SaleStatus='訂單已完成'
    '''.format(B_SalerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_finished)
        datas_finished = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_finished)

    return render_template("user_information_sellerpage.html", datas_uploaded = datas_uploaded, datas_processing = datas_processing, datas_finished = datas_finished)

# [賣家介面] 下架書籍
@app.route('/book_delete/<B_BookID>')
def book_delete(B_BookID):
    sql_disable_fk_check = "SET FOREIGN_KEY_CHECKS=0;"
    sql_delete_book = "DELETE FROM book_information WHERE B_BookID='{}';".format(B_BookID)
    sql_enable_fk_check = "SET FOREIGN_KEY_CHECKS=1;"
    
    # "ALTER TABLE" 刪除order_information表中的外部關鍵字約束
    sql_alter_fk_constraint = "ALTER TABLE order_information DROP FOREIGN KEY order_information_ibfk_3;"
    
    insert_or_update_data(sql_disable_fk_check)
    insert_or_update_data(sql_alter_fk_constraint)
    insert_or_update_data(sql_delete_book)
    insert_or_update_data(sql_enable_fk_check)
    print(sql_alter_fk_constraint)
    print(sql_delete_book)

    return redirect('/user_information_sellerpage') # 重新導向至賣家介面(尚未導至已上架分頁)

# [賣家介面] 我已出貨按鈕 (B_SaleStatus --> '賣家已出貨')
@app.route('/do_saler_delivered/<B_BookID>')
def saler_delivered(B_BookID):
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "update book_information set B_SaleStatus='賣家已出貨' where B_BookID={}".format(B_BookID)
        cursor.execute(sql)
        conn.commit()

        # Fetching book details for email
        book_sql = "select * from book_information where B_BookID=" + B_BookID
        cursor.execute(book_sql)
        book_datas = cursor.fetchall()
        if book_datas:
            book = book_datas[0]
        else:
            book = None

        # Fetching buyer's email and locker_id
        buyer_info_sql = "select A_Email, locker_id from account_manage join order_information on account_manage.A_StuID = order_information.A_BuyerID where order_information.B_BookID=" + B_BookID
        cursor.execute(buyer_info_sql)
        buyer_info = cursor.fetchone()
        buyer_email = buyer_info['A_Email']
        locker_id = buyer_info['locker_id']

        # Send email to the buyer
        send_email_Buyer(buyer_email, session['A_StuID'], book['B_BookName'], locker_id)

    finally:
        conn.close()

    return redirect('/user_information_sellerpage') # 重新導向至賣家介面


# [賣家介面] 確認按鈕 (B_SaleStatus --> '賣家已確認')
@app.route('/do_saler_check/<B_BookID>')
def saler_check(B_BookID):
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "update book_information set B_SaleStatus='賣家已確認' where B_BookID={}".format(B_BookID)
        cursor.execute(sql)
        conn.commit()

        # Fetching book details for email
        book_sql = "select * from book_information where B_BookID=" + B_BookID
        cursor.execute(book_sql)
        book_datas = cursor.fetchall()
        if book_datas:
            book = book_datas[0]
        else:
            book = None

        # Fetching buyer's email
        buyer_info_sql = "select A_Email from account_manage join order_information on account_manage.A_StuID = order_information.A_BuyerID where order_information.B_BookID=" + B_BookID
        cursor.execute(buyer_info_sql)
        buyer_info = cursor.fetchone()
        buyer_email = buyer_info['A_Email']

        # Send email to the buyer
        send_email_Buyer(buyer_email, session['A_StuID'], book['B_BookName'])

    finally:
        conn.close()

    return redirect('/user_information_sellerpage') # 重新導向至賣家介面


# [賣家介面] 取消按鈕 (B_SaleStatus --> '賣家已上架'，可重新被搜尋及下單)
@app.route('/do_saler_cancel/<B_BookID>')
def saler_cancel(B_BookID):
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Fetching book details for email
        book_sql = "select * from book_information where B_BookID=" + B_BookID
        cursor.execute(book_sql)
        book_datas = cursor.fetchall()
        if book_datas:
            book = book_datas[0]
        else:
            book = None

        # Fetching buyer's email
        buyer_info_sql = "select A_Email from account_manage join order_information on account_manage.A_StuID = order_information.A_BuyerID where order_information.B_BookID=" + B_BookID
        cursor.execute(buyer_info_sql)
        buyer_info = cursor.fetchone()
        buyer_email = buyer_info['A_Email']

        # Update sale status and delete order
        sql_status = "update book_information set B_SaleStatus='賣家已上架' where B_BookID={}".format(B_BookID)
        sql_order = "delete from order_information where B_BookID={}".format(B_BookID)
        cursor.execute(sql_status)
        cursor.execute(sql_order)
        conn.commit()

        # Send email to the buyer
        send_email_Buyer(buyer_email, session['A_StuID'], book['B_BookName'])

    finally:
        conn.close()

    return redirect('/user_information_sellerpage') # 重新導向至賣家介面


# [賣家介面] 賣家評價功能
@app.route('/do_user_information_seller_rating/<B_BookID>', methods=['POST'])
def user_information_seller_rating(B_BookID):
    data = request.get_json()
    O_SalerRating = data.get("O_SalerRating")
    sql = f'''
    update order_information set O_SalerRating={O_SalerRating}
    where B_BookID={B_BookID}
    '''
    print(sql)
    insert_or_update_data(sql)
    return jsonify({'status': 'success'}), 200

    #return redirect('/user_information_sellerpage?tab=finished') #重新導向至已完成分頁

# [交易紀錄] 顯示頁面
@app.route('/user_information_record')
def show_user_information_record():
    A_BuyerID = session.get('A_StuID')

    # 交易紀錄(B_SaleStatus='訂單已完成')
    sql_finished = '''
    select b.B_BookID, b.B_BookName, b.B_BookPic, b.B_SaleStatus, o.O_SalerRating, o.O_BuyerRating from book_information b, order_information o 
    where b.B_BookID = o.B_BookID and b.B_SaleStatus='訂單已完成' and o.A_BuyerID='{}'
    '''.format(A_BuyerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_finished)
        datas_finished = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_finished)

    return render_template("user_information_record.html", datas_finished = datas_finished)


# 顯示[查詢訂單] 篩選條件：A_BuyerID、B_SaleStatus
@app.route('/user_information_orders')
def show_user_information_orders():
    A_BuyerID = session.get('A_StuID')

    # 已下單(B_SaleStatus='買家已下單' or '賣家已確認')
    sql_ordered = '''
    select b.B_BookID, b.B_BookName, b.B_BookPic, b.B_SaleStatus from book_information b, order_information o 
    where b.B_BookID = o.B_BookID and o.A_BuyerID='{}' 
    and (b.B_SaleStatus='買家已下單' or b.B_SaleStatus='賣家已確認')
    '''.format(A_BuyerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_ordered)
        datas_ordered = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_ordered)

    # 進行中(B_SaleStatus='賣家已出貨')
    sql_processing = '''
    select b.B_BookID, b.B_BookName, b.B_BookPic, b.B_SaleStatus from book_information b, order_information o 
    where b.B_BookID = o.B_BookID and o.A_BuyerID='{}' 
    and b.B_SaleStatus='賣家已出貨'
    '''.format(A_BuyerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_processing)
        datas_processing = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_processing)

    # 已完成(B_SaleStatus='訂單已完成')
    sql_finished = '''
    select b.B_BookID, b.B_BookName, b.B_BookPic, b.B_SaleStatus, o.O_SalerRating, o.O_BuyerRating from book_information b, order_information o 
    where b.B_BookID = o.B_BookID and b.B_SaleStatus='訂單已完成' and o.A_BuyerID='{}'
    '''.format(A_BuyerID)
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql_finished)
        datas_finished = cursor.fetchall()
    except Exception as e:
        logging.exception("Error occurred during user_information_sellerpage")
        return "An error occurred during user_information_sellerpage. Please check the error log for more information.", 500
    finally:
        conn.close()
    print(sql_finished)

    return render_template("user_information_orders.html", datas_ordered = datas_ordered, datas_processing = datas_processing, datas_finished = datas_finished)

# [查詢訂單] 取消按鈕 (B_SaleStatus --> '賣家已上架'，可重新被搜尋及下單)
@app.route('/do_buyer_cancel/<B_BookID>')
def buyer_cancel(B_BookID):
    sql_ststus = "update book_information set B_SaleStatus='賣家已上架' where B_BookID={}".format(B_BookID)
    sql_order = "delete from order_information where B_BookID={}".format(B_BookID)

    insert_or_update_data(sql_ststus) # 更新B_SaleStatus狀態
    insert_or_update_data(sql_order) # 刪除訂單紀錄
    print(sql_ststus)
    print(sql_order)
    return redirect('/user_information_orders') # 重新導向至查詢訂單(尚未導至已下單分頁)

# [查詢訂單] 完成訂單按鈕 (B_SaleStatus --> '訂單已完成')
@app.route('/do_buyer_complete/<B_BookID>')
def buyer_complete(B_BookID):
    sql = "update book_information set B_SaleStatus='訂單已完成' where B_BookID={}".format(B_BookID)
    print(sql)
    insert_or_update_data(sql)
    return redirect('/user_information_orders') # 重新導向至查詢訂單


# [查詢訂單] 買家評價功能
@app.route('/do_user_information_buyer_rating/<B_BookID>', methods=['POST'])
def user_information_buyer_rating(B_BookID):
    # print(request.form)
    # O_BuyerRating = request.form.get("O_BuyerRating")
    # sql = f'''
    # update order_information set O_BuyerRating={O_BuyerRating}
    # where B_BookID={B_BookID}
    # '''
    # print(sql)
    # insert_or_update_data(sql)
    
    data = request.get_json()
    O_BuyerRating = data.get("O_BuyerRating")
    sql = f'''
    update order_information set O_BuyerRating={O_BuyerRating}
    where B_BookID={B_BookID}
    '''
    print(sql)
    insert_or_update_data(sql)
    return jsonify({'status': 'success'}), 200

  #  return redirect('/user_information_orders?tab=finished') #重新導向至已完成分頁

# [我要申訴] 顯示網頁
@app.route('/grievance')
def show_grievance():
    return render_template("grievance.html")

# [上架] 顯示網站
@app.route('/book_create')
def show_book_create():
    return render_template("book_create.html")

# [上架] 接收表單提交的數據
@app.route('/do_book_create', methods=['POST'])
def book_create():

    # 儲存圖片
    file = request.files['B_BookPic']
    if file.filename != '':
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        print('--picture save successfully:' + file.filename)

    print(request.form)
    B_BookName = request.form.get("B_BookName")
    B_ISBN = request.form.get("B_ISBN")
    B_Author = request.form.get("B_Author")
    B_BookVersion = request.form.get("B_BookVersion")
    B_BookMajor = request.form.get("B_BookMajor")
    B_LessonName = request.form.get("B_LessonName")
    B_BookPic = file.filename
    B_BookStatus = request.form.get("B_BookStatus")
    B_UsedStatus = request.form.get("B_UsedStatus")
    B_UsedByTeacher = request.form.get("B_UsedByTeacher")
    B_Extra_Info = request.form.get("B_Extra_Info")
    B_Price = request.form.get("B_Price")
    B_SalerID = session['A_StuID']
    sql = f'''
    insert into book_information(B_BookName, B_ISBN, B_Author, B_BookVersion, B_BookMajor, B_LessonName, B_BookPic, B_BookStatus, B_UsedStatus, B_UsedByTeacher, B_Extra_Info, B_Price, B_SalerID)
    values('{B_BookName}', '{B_ISBN}', '{B_Author}', '{B_BookVersion}', '{B_BookMajor}', '{B_LessonName}', '{B_BookPic}', {B_BookStatus}, '{B_UsedStatus}', '{B_UsedByTeacher}', '{B_Extra_Info}', {B_Price},'{B_SalerID}')
    '''
    print(sql)
    insert_or_update_data(sql)
#    return "Book added successfully!"
    return redirect(url_for('show_user_information_sellerpage'))  #trying:重新導向並用彈出式視窗顯示成功訊息

# [修改書籍資訊] 顯示網站
@app.route('/book_update/<B_BookID>')
def show_book_update(B_BookID):
    sql = "select * from book_information where B_BookID=" + B_BookID
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        datas = cursor.fetchall()
        book = datas[0]
    finally:
        conn.close()
    print(sql)
    return render_template("book_update.html", book = book)

# [修改書籍資訊] 接收表單提交的數據
@app.route('/do_book_update', methods=['POST'])
def book_update():
    # 儲存圖片
    file = request.files['B_BookPic']
    if file.filename != '':
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        print('--new book picture:' + file.filename)
        B_BookPic = file.filename
    else:
        B_BookPic = ''  # Set it to empty if no file is uploaded

    print(request.form)
    B_BookID = request.form.get("B_BookID")
    B_BookName = request.form.get("B_BookName")
    B_ISBN = request.form.get("B_ISBN")
    B_Author = request.form.get("B_Author")
    B_BookVersion = request.form.get("B_BookVersion")
    B_BookMajor = request.form.get("B_BookMajor")
    B_LessonName = request.form.get("B_LessonName")
    B_BookStatus = request.form.get("B_BookStatus")
    B_UsedStatus = request.form.get("B_UsedStatus")
    B_UsedByTeacher = request.form.get("B_UsedByTeacher")
    B_Extra_Info = request.form.get("B_Extra_Info")
    B_Price = request.form.get("B_Price")

    sql = f'''
    update book_information set B_BookName='{B_BookName}', B_ISBN='{B_ISBN}', B_Author='{B_Author}', B_BookVersion='{B_BookVersion}', 
    B_BookMajor='{B_BookMajor}', B_LessonName='{B_LessonName}', B_BookStatus={B_BookStatus}, 
    B_UsedStatus='{B_UsedStatus}', B_UsedByTeacher='{B_UsedByTeacher}', B_Extra_Info='{B_Extra_Info}', B_Price={B_Price}
    '''
    if B_BookPic != '': 
        sql += f", B_BookPic='{B_BookPic}'"  #有傳新圖片才更新這欄SQL
    sql += f" where B_BookID={B_BookID}"

    print(sql)
    insert_or_update_data(sql)
#    return "Information updated successfully!"
    return redirect(url_for('show_user_information_sellerpage'))  #trying:重新導向並用彈出式視窗顯示成功訊息

# [書籍列表] 顯示網站
@app.route('/book_display')
def show_book_display():
    sql = "select B_BookID, B_BookName, B_BookPic, B_Price from book_information"
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        datas = cursor.fetchall()
    finally:
        conn.close()
    print(sql)
    return render_template("book_display.html", datas = datas)

# [依"標籤"尋找書籍] 接收搜尋的數據
@app.route('/do_book_search', methods=['GET'])
def book_search():
    search_str = request.args.get('search_str')
    session['search_str'] = search_str  # 將 search_str 儲存在 session 中

    # SQL語法 (搜索欄位: 書名、作者、科系、課程、老師)
    sql = f'''select B_BookID, B_BookName, B_BookPic, B_Price from book_information where 
    ((B_BookName like '%{search_str}%') or (B_Author like '%{search_str}%') or (B_BookMajor like '%{search_str}%') 
    or (B_LessonName like '%{search_str}%') or (B_UsedByTeacher like '%{search_str}%'))
    and B_SaleStatus='賣家已上架'
    '''
    # 每次重新搜尋就重置sorting設定
    if 'sorting' in session:
        del session['sorting']  # 從 session 字典中刪除 'sorting' 鍵

    return show_book_search(sql)

# [依"標籤"尋找書籍] 為搜尋結果排序
@app.route('/do_book_sort', methods=["POST"])
def book_sort():
    sorting = request.form.get('sorting', "") # 若沒抓到值，預設為""
    session['sorting'] = sorting  # 將 sorting 儲存在 session 中
    search_str = session.get('search_str')

    # SQL語法 (搜索欄位: 書名、作者、科系、課程、老師)
    sql = f'''select B_BookID, B_BookName, B_BookPic, B_Price from book_information where 
    ((B_BookName like '%{search_str}%') or (B_Author like '%{search_str}%') or (B_BookMajor like '%{search_str}%') 
    or (B_LessonName like '%{search_str}%') or (B_UsedByTeacher like '%{search_str}%'))
    and B_SaleStatus='賣家已上架'
    '''
    # 加上排序
    if sorting == "B_Price_asc":
        sql += " order by B_Price asc"
    elif sorting == "B_BookStatus_desc":
        sql += " order by B_BookStatus desc"
    return show_book_search(sql)

# [依"標籤"尋找書籍] 顯示網站，
@app.route('/book_search/<search_str>')
def show_book_search(sql):

    # 抓取 search_str (搜尋字詞)
    search_str = session.get('search_str')
    # 抓取 sorting 設定以在前端顯示radio已點按狀態
    sorting = session.get('sorting')

    # 執行接收到的SQL
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        datas = cursor.fetchall()
        print(datas)
    finally:
        conn.close()
    print(sql)
    return render_template("book_search.html", datas = datas, search_str = search_str, sorting = sorting)

#顯示書籍詳細資訊
from flask import request
import datetime

@app.route('/book_detail/<B_BookID>', methods=['GET', 'POST'])
def show_book_detail(B_BookID):
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Handle POST request
        if request.method == 'POST':
            A_StuID = session.get('A_StuID')  # Get the user ID from the session
            C_CommentText = request.form.get('C_CommentText')  # Get the comment text from the form
            C_ParentCommentID = request.form['C_ParentCommentID'] or None  # Convert empty strings to None

            # Insert new comment into the database
            insert_comment_sql = """
            INSERT INTO comments (A_StuID, B_BookID, C_CommentText, C_CommentTime, C_ParentCommentID)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_comment_sql, (A_StuID, B_BookID, C_CommentText, datetime.datetime.now(), C_ParentCommentID))
            conn.commit()

            # Fetching book details for email
            book_sql = "select * from book_information where B_BookID=" + B_BookID
            cursor.execute(book_sql)
            book_datas = cursor.fetchall()
            if book_datas:
                book = book_datas[0]
            else:
                book = None

            # Fetching saler's email
            saler_email_sql = "select A_Email from account_manage where A_StuID='" + book['B_SalerID'] + "'"
            cursor.execute(saler_email_sql)
            saler_email = cursor.fetchone()['A_Email']

            # If this is a new comment, send email to the book's seller
            if C_ParentCommentID is None:
                send_email_Notification(saler_email, book['B_BookName'])
            # If this is a reply, send email to the original commenter
            else:
                original_commenter_email_sql = """
                select account_manage.A_Email 
                from account_manage join comments on account_manage.A_StuID = comments.A_StuID 
                where comments.C_CommentID=%s
                """
                cursor.execute(original_commenter_email_sql, C_ParentCommentID)
                original_commenter_email = cursor.fetchone()['A_Email']
                send_email_Notification(original_commenter_email, book['B_BookName'])

            return redirect(url_for('show_book_detail', B_BookID=B_BookID))

        # Fetching book details
        book_sql = "select * from book_information where B_BookID=" + B_BookID
        cursor.execute(book_sql)
        book_datas = cursor.fetchall()
        if book_datas:
            book = book_datas[0]
            session['B_SalerID'] = book['B_SalerID']
        else:
            book = None

        # Fetching comments
        comments_sql = "select * from comments where B_BookID=" + B_BookID + " ORDER BY C_CommentTime DESC"
        cursor.execute(comments_sql)
        comments = cursor.fetchall()  # Fetching all the comments related to this book

    finally:
        conn.close()

    # Return the book detail and comments information to the template
    return render_template("book_detail.html", book=book, comments=comments)


#定義寄信功能的function(寄給買家)
def send_email_Buyer(to_email, A_BuyerID, book_name, locker_id):
    content = MIMEMultipart()
    content["subject"] = (f"您在輔大二手書網站 購買 {book_name} 的訂單已成立，但尚未被賣家同意!")
    content["from"] = "wsx2244667@gmail.com"
    content["to"] = to_email
    content.attach(MIMEText(f"已經成功下訂，請耐心等候賣家同意您的訂單!"))

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("wsx2244667@gmail.com", "gpitruqqyaubmocl")
            smtp.send_message(content)
            print("Email sent!")
        except Exception as e:
            print("Error message: ", e)
            
#賣家按下確認按鈕，將訂單確立，寄信給買家
def send_email_Buyer(to_email, A_BuyerID, book_name, locker_id):
    content = MIMEMultipart()
    content["subject"] = (f"您在輔大二手書網站 購買 {book_name} 的訂單已被同意!")
    content["from"] = "wsx2244667@gmail.com"
    content["to"] = to_email
    content.attach(MIMEText(f"您在輔大二手書網站 購買 {book_name} 訂單已被同意，請耐心等待賣家出貨!"))

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("wsx2244667@gmail.com", "gpitruqqyaubmocl")
            smtp.send_message(content)
            print("Email sent!")
        except Exception as e:
            print("Error message: ", e)
            
#賣家按下取消按鈕，將訂單取消，寄信給買家
def send_email_Buyer(to_email, A_BuyerID, book_name, locker_id):
    content = MIMEMultipart()
    content["subject"] = (f"您在輔大二手書網站下訂的訂單已被取消!")
    content["from"] = "wsx2244667@gmail.com"
    content["to"] = to_email
    content.attach(MIMEText(f"您在輔大二手書網站下訂訂單已被取消，再看看其他貨品吧!"))

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("wsx2244667@gmail.com", "gpitruqqyaubmocl")
            smtp.send_message(content)
            print("Email sent!")
        except Exception as e:
            print("Error message: ", e)
            
#賣家按下我已出貨按鈕，將書籍出貨，寄信給買家
def send_email_Buyer(to_email, A_BuyerID, book_name, locker_id):
    content = MIMEMultipart()
    content["subject"] = (f"您在輔大二手書網站 購買 {book_name} 的訂單即將完成，請前往面交櫃取書!")
    content["from"] = "wsx2244667@gmail.com"
    content["to"] = to_email
    content.attach(MIMEText(f"請前往 {locker_id} 號 面交櫃進行付款與拿取您的書籍!，付款完畢後也請記得給評價ㄛ~"))

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("wsx2244667@gmail.com", "gpitruqqyaubmocl")
            smtp.send_message(content)
            print("Email sent!")
        except Exception as e:
            print("Error message: ", e)

#寄信功能的function(寄給賣家)，通知有人下訂
def send_email_Saler(to_email, A_SalerID, book_name, locker_id):
    content = MIMEMultipart()
    content["subject"] = (f"您在輔大二手書網站上架的 {book_name} 書籍已被下訂!")
    content["from"] = "wsx2244667@gmail.com"
    content["to"] = to_email
    content.attach(MIMEText(f"如果您有意願交易或是確認詳細訂單，請前往賣家頁面!"))

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("wsx2244667@gmail.com", "gpitruqqyaubmocl")
            smtp.send_message(content)
            print("Email sent!")
        except Exception as e:
            print("Error message: ", e)
#發送ㄊㄓ        
def send_email_Notification(to_email, book_name,):
    content = MIMEMultipart()
    content["subject"] = (f"在 {book_name} 中的交流板裡有關於您的留言!")
    content["from"] = "wsx2244667@gmail.com"
    content["to"] = to_email
    content.attach(MIMEText(f"在您已上架或是您互動過的 {book_name} 書中的交流版有新訊息! 請前往查看!"))

    with smtplib.SMTP(host="smtp.gmail.com", port="587") as smtp:
        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.login("wsx2244667@gmail.com", "gpitruqqyaubmocl")
            smtp.send_message(content)
            print("Email sent!")
        except Exception as e:
            print("Error message: ", e)

#點擊後購買後產生訂單
@app.route('/order', methods=['POST'])
def order_book():
    B_BookID = request.form['B_BookID']
    A_BuyerID = session.get('A_StuID')
    O_OrderTime = datetime.datetime.now()
    O_LockerID = 1
    O_SalerRating = 0
    O_BuyerRating = 0
    # get saler_id from book_information table
    conn = get_conn()
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("select B_SalerID FROM book_information WHERE B_BookID = %s", (B_BookID,))
    result = cursor.fetchone()
    if result is None:
        return 'Book not found'+ B_BookID, 404
    B_SalerID = result['B_SalerID'] # Here, use 'B_SalerID' instead of B_SalerID
    
    # insert order into order_information table
    cursor.execute(
    "INSERT INTO order_information (O_OrderTime, O_LockerID, B_BookID, B_SalerID, A_BuyerID, O_SalerRating, O_BuyerRating) VALUES (%s, %s, %s, %s, %s, %s, %s)",
    (O_OrderTime, O_LockerID, B_BookID, B_SalerID, A_BuyerID, O_SalerRating, O_BuyerRating)
)

    conn.commit()
    
    # Fetch the necessary data for the email
    cursor.execute("SELECT A_Email FROM account_manage WHERE A_StuID = %s", (A_BuyerID,))
    result = cursor.fetchone()
    if result is not None:
        A_Email_Buyer = result['A_Email']
    cursor.execute("SELECT A_Email FROM account_manage WHERE A_StuID = %s", (B_SalerID,))
    result = cursor.fetchone()
    if result is not None:
        A_Email_Saler = result['A_Email']
    cursor.execute("SELECT B_BookName FROM book_information WHERE B_BookID = %s", (B_BookID,))
    result = cursor.fetchone()
    if result is not None:
        B_BookName = result['B_BookName']
    cursor.close()
    
    send_email_Buyer(A_Email_Buyer,A_BuyerID,B_BookName,O_LockerID)
    send_email_Saler(A_Email_Saler,B_SalerID,B_BookName,O_LockerID)

    # [查看書籍詳細資訊] 購買按鈕 (B_SaleStatus --> '買家已下單')
    sql_status = "update book_information set B_SaleStatus='買家已下單' where B_BookID={}".format(B_BookID)
    print(sql_status)
    insert_or_update_data(sql_status)

#    return 'Order Placed Successfully'
    return redirect('/book_detail/{}'.format(B_BookID)) # 重新導向至書籍詳細資訊

#測試comments的功能用
@app.route('/comments')
def comment():
    A_CurrentuserID = session.get('A_StuID')
    return render_template("comments.html", A_StuID = A_CurrentuserID)

#測試topic頁面功能
@app.route('/topics_listing')
def topics_listen():
    return render_template("topics-listing.html")

#測試contact頁面功能
@app.route('/contact')
def contact():
    return render_template("contact.html")

#申訴管道頁面
@app.route('/grievance')
def grievance_Procedure():
    return render_template("grievance.html")

# 測試display(v3) 
@app.route('/display')
def show_display():
    # 搜索欄位: 書名、作者、科系、課程、老師
    # 僅篩選狀態為'賣家已上架'的書籍
    sql = f'''select B_BookID, B_BookName, B_BookPic, B_Price from book_information
    '''
    conn = get_conn()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(sql)
        datas = cursor.fetchall()
        print(datas)
    finally:
        conn.close()
    print(sql)

    return render_template("book_display3.html", datas = datas)

# 執行
if __name__ == '__main__': # 如果以主程式執行
    app.run(debug=True) 