from flask import Flask, render_template, request, redirect, session,url_for
import pymysql.cursors
import stripe
import paypalrestsdk
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # Enable CORS globally or selectively for certain routes

app.secret_key = 'your_secret_key'
stripe.api_key = "sk_test_51P9lKBSFGTVxz9u1OZBTKpGnHE36jF6ROio659d6eUXAtzgmgErpYl8jgzxoyxUafFQESGd8Lpyn7VlBO5ROL4mq00E2XcBVs3"
paypalrestsdk.configure({
  "mode": "sandbox",  # sandbox or live
  "client_secret": "EBYA831Y8H6edzr5AwEVVb35zxYNkjwYWfxv9cDKiU0V5ZHYvpY633riLMCkEjJCAAmWvc2188eDeZ2i",
  "client_id": "AYyyrH-ib8gGSsUIY4eBkH61sbGKupv1IVBfv4-F6SguR5I6RT2-kgfpbkAO6qcfDzs-5pU0easNdsok"
})
# Database connection setup
def get_db_connection():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='sH1012@v',
                           db='sql_7invoicing',
                           charset='utf8mb4',
                           cursorclass=pymysql.cursors.DictCursor)

@app.route('/')
def login_signup():
    return render_template('index.html', user_id=session.get('user_id'))

@app.route('/error')
def error():
    return render_template('error.html', user_id=session.get('user_id'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Fetch form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # Insert user data into 'user' table
                sql = "INSERT INTO `user` (`first_name`, `last_name`, `username`, `email`, `password`) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(sql, (first_name, last_name, username, email, password))
                connection.commit()

                # Fetch the user_id of the newly registered user
                cursor.execute("SELECT `user_id` FROM `user` WHERE `email` = %s", (email,))
                user_id = cursor.fetchone()['user_id']
                
                session['user_id'] = user_id
                return redirect('/login')
        except Exception as e:
            # Handle exceptions
            print("Exception:", e)
            return render_template('signup.html', error="Error occurred during signup.")
        finally:
            connection.close()
    else:
        # Return the signup template for GET requests
        return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            connection = get_db_connection()
            with connection.cursor() as cursor:
                # Fetch user data from 'user' table based on email and password
                sql = "SELECT * FROM `user` WHERE `email` = %s AND `password` = %s"
                cursor.execute(sql, (email, password))
                user = cursor.fetchone()

                if user:
                    session['user_id'] = user['user_id']
                    return redirect('/ask')
                else:
                    return render_template('login.html', error="Invalid email or password.")
        except Exception as e:
            print("Exception:", e)
            return render_template('login.html', error="Error occurred during login.")
        finally:
            connection.close()
    else:
        # Return the login template for GET requests
        return render_template('login.html')

@app.route('/ask', methods=['GET', 'POST'])
def ask():
    if 'user_id' not in session:
        return redirect('/')

    if request.method == 'POST':
        # Initialize DB connection
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                account_type = request.form.get('account_type')
                company_name = request.form.get('company_name') if account_type == 'Business' else None
                industry = request.form.get('industry') if account_type == 'Business' else None
                business_email = request.form.get('business_email') if account_type == 'Business' else None
                role_request = 'Request' in request.form.getlist('role')
                role_expert = 'Expert' in request.form.getlist('role')
                expertise_request = request.form.getlist('expertiseRequest[]') if role_request else []
                expertise_expert = request.form.getlist('expertiseExpert[]') if role_expert else []


                # Update account information
                account_id_query = "SELECT `account_id` FROM `account` WHERE `type` = %s"
                cursor.execute(account_id_query, (account_type,))
                account_result = cursor.fetchone()
                if account_result is None:
                    raise ValueError("Account type not found.")
                account_id = account_result['account_id']
                
                if account_type == 'Business':
                    # Insert or update company information if not exists
                    company_query = "INSERT INTO `company` (`name`, `industry`) VALUES (%s, %s) ON DUPLICATE KEY UPDATE `industry` = VALUES(`industry`)"
                    cursor.execute(company_query, (company_name, industry))
                    company_id = cursor.lastrowid or cursor.execute("SELECT `company_id` FROM `company` WHERE `name` = %s", (company_name,)) 

                    # Update user_account for business
                    user_account = """
                    INSERT INTO `user_account`
                    (`account_id`, `company_id`, `business_email`, `user_id`) VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(user_account, (account_id, company_id, business_email, session['user_id']))
                else:
                    # Update user_account for individual
                    user_account = " INSERT INTO `user_account`  (`account_id`, `user_id`) VALUES (%s, %s)"
                    cursor.execute(user_account, (account_id, session['user_id']))
                print(4)
                # Handling roles and expertise
                
                # Handling roles and expertise
                if role_request:
                    for expertise_id in expertise_request:
                        insert_user_role = """
                            INSERT INTO `user_role` (`user_id`, `role_id`, `expertise_id`) VALUES (%s, (SELECT `role_id` FROM `role` WHERE `type` = 'Request'), %s)
                        """
                        cursor.execute(insert_user_role, (session['user_id'], expertise_id))

                if role_expert:
                    for expertise_id in expertise_expert:
                        insert_user_role = """
                            INSERT INTO `user_role` (`user_id`, `role_id`, `expertise_id`) VALUES (%s, (SELECT `role_id` FROM `role` WHERE `type` = 'Expert'), %s)
                           """
                        cursor.execute(insert_user_role, (session['user_id'], expertise_id))

                # Commit changes to the database
                connection.commit()
                return redirect('/plan')
        except Exception as e:
            print("Exception:", e)
            return render_template('ask.html', error="Error occurred while updating user information.", roles=[], expertise_areas=[], account_types=[])
        finally:
            connection.close()
    else:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Fetch roles
            cursor.execute("SELECT `role_id`, `type` FROM `role`")
            roles = cursor.fetchall()
            
            # Fetch expertise areas
            cursor.execute("SELECT `expertise_id`, `name` FROM `expertise`")
            expertise_areas = cursor.fetchall()
            cursor.execute('SELECT * FROM account')
            account_types = cursor.fetchall()

        return render_template('ask.html', roles=roles, expertise_areas=expertise_areas,account_types=account_types)
# Import datetime module correctly

@app.route('/plan', methods=['GET', 'POST'])
def plan():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    user_roles = get_user_roles(user_id)
    is_requester = 1 in user_roles
    is_expert = 2 in user_roles
    roles = ['Both'] if is_requester and is_expert else (['Expert'] if is_expert else ['Request'])
    payment_status=[]

    plans = []  # Define an empty list here

    if request.method == 'POST':
        try:
            plan_id = request.form.get('plan_id')
            print("Received Plan ID:", plan_id)  # Debug line
            if not plan_id:
                return render_template('plan.html', plans=plans, is_requester=is_requester, is_expert=is_expert, error="Plan ID is missing. Please select a plan.")
            
            start_date = datetime.datetime.now() # Use datetime.now() to get the current date and time
            connection = get_db_connection()
            with connection.cursor() as cursor:
                    cursor.execute("SELECT `price` FROM `subscription_plan` WHERE `plan_id` = %s", (plan_id,))
                    plan_price = cursor.fetchone()
                    cursor.execute("SELECT `payment_status` FROM `user_subscription` WHERE `user_id` = %s", (user_id,))
                    payment_status = cursor.fetchall()
                    print(payment_status)
                    
                    

                    # Provide a default message if no statuses are found

           


            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT `duration_months` FROM `subscription_plan` WHERE `plan_id` = %s", (plan_id,))
                    plan_duration = cursor.fetchone()['duration_months']
                    end_date = start_date + relativedelta(months=plan_duration)

                    cursor.execute(
                        "INSERT INTO `user_subscription` (`user_id`, `plan_id`, `start_date`, `end_date`) VALUES (%s, %s, %s, %s)",
                        (user_id, plan_id, start_date, end_date)
                    )
                    
                    connection.commit()

            except Exception as e:
                print("Exception:", e)
                connection.rollback()
            finally:
                connection.close()

            # After processing the plan, redirect to the payment route
            return render_template('payment.html', user_id=session['user_id'],plan_price=plan_price['price'],plan_id=plan_id,payment_status=payment_status)

        except KeyError as ke:
            return render_template('plan.html', plans=plans, is_requester=is_requester, is_expert=is_expert, error="Plan ID is missing. Please select a plan.")

    # Add a return statement for the case when the request method is not POST
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT * FROM subscription_plan WHERE `role_type` IN (%s)"
            in_p = ', '.join(list(map(lambda x: '%s', roles)))
            query = query % in_p
            cursor.execute(query, roles)
            plans = cursor.fetchall()
            
    finally:
        connection.close()
    
    return render_template('plan.html', plans=plans, is_requester=is_requester, is_expert=is_expert)






from datetime import datetime


from flask import redirect, render_template, session, request

@app.route('/payment/<float:plan_price>/<int:plan_id>', methods=['GET', 'POST'])
def payment(plan_price, plan_id):
    if 'user_id' not in session:
        return redirect('/login')  
    
    
        # Handle the successful payment
        # Update the database with payment details
        

    # Render the payment page with PayPal button
    return render_template('payment.html', plan_price=plan_price,plan_id=plan_id)


# Update your payment.html template to include the PayPal button container
# Make sure to integrate the PayPal JavaScript SDK as shown in your original code


from flask import request

@app.route('/payment_success', methods=['POST'])
def payment_success():
    data = request.json  # Read the JSON data from the request
    plan_price = data.get('plan_price')
    plan_id = data.get('plan_id')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert payment record into user_payment
            cursor.execute(
                "INSERT INTO `user_payment` (`user_id`, `plan_id`, `payment_date`, `amount`, `payment_status`) VALUES (%s, %s, %s, %s, %s)",
                (session['user_id'], plan_id, datetime.datetime.now(), plan_price, "Successful")
            )

            # Update user_subscription with payment status
            cursor.execute(
                "UPDATE `user_subscription` SET `payment_status` = 'Paid' WHERE `user_id` = %s",
                (session['user_id'],)
            )

            connection.commit()  # Commit the changes
    except Exception as e:
        print("Exception:", e)  # Log the exception for debugging
    finally:
        connection.close()

    # Redirect to the dashboard after successful payment
    return redirect('/dashboard')


    # Redirect to the dashboard after successful payment
    


  
    

    







@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    user_roles = get_user_roles(user_id)
    is_expert = False 
    is_admin = False  # Initialize is_admin here
    shared_queries_with_expert = []
    credit_card_info = None # Variable to determine if the user is an expert
    connection = get_db_connection()
    
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM user_role WHERE user_id = %s AND role_id = (SELECT role_id FROM role WHERE type = "Expert")', (user_id,))
            if cursor.fetchone():
                is_expert = True
            # Get user details and roles
            cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
            user = cursor.fetchone()

            cursor.execute("SELECT * FROM credit_card WHERE user_id = %s", (user_id,))
            credit_card_info = cursor.fetchone()

            cursor.execute('SELECT * FROM admin WHERE TRIM(email)  = %s', (user['email'],))
            if cursor.fetchone():
                is_admin = True
            
            print(is_admin)

            cursor.execute('SELECT * FROM query WHERE Request_user_id = %s', (user_id,))
            queries = cursor.fetchall()

            if is_expert:
                cursor.execute('''
                    SELECT q.*, ue.username AS expert_username
                    FROM query_expert qe
                    INNER JOIN query q ON qe.query_id = q.query_id
                    INNER JOIN user ue ON qe.expert_user_id = ue.user_id
                    WHERE qe.expert_user_id = %s
                ''', (user_id,))
                shared_queries_with_expert = cursor.fetchall()
            
            # If the user is a requester, fetch expert users with expertise in the requested area
            if 1  in user_roles:
                cursor.execute('''
                    SELECT u.username, u.user_id,u.first_name, u.last_name, ep.price, ep.place, e.name as expertise
                    FROM user u
                    INNER JOIN user_role ur ON u.user_id = ur.user_id
                    INNER JOIN expertise e ON ur.expertise_id = e.expertise_id
                    INNER JOIN expert_profile ep ON u.user_id = ep.user_id
                    WHERE ur.role_id = (SELECT role_id FROM role WHERE type = 'Expert')
                    AND e.expertise_id IN (SELECT expertise_id FROM user_role WHERE user_id = %s AND role_id = (SELECT role_id FROM role WHERE type = 'Request'))
                ''', (user_id,))
                expert_users = cursor.fetchall()
            else:
                expert_users = None
            
    finally:
        connection.close()
    
    return render_template('dashboard.html', credit_card_info=credit_card_info,user=user, is_expert=is_expert,  is_admin=is_admin,expert_users=expert_users,user_roles=user_roles, queries=queries, shared_queries=shared_queries_with_expert,user_id=user_id)



def get_expertise_for_user(user_id):
    connection = get_db_connection()
    expertise = []
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM expertise WHERE expertise_id IN (SELECT expertise_id FROM user_role WHERE user_id = %s)"
            cursor.execute(sql, (user_id,))
            expertise = cursor.fetchall()
    except Exception as e:
        print("Exception:", e)
    finally:
        connection.close()
    return expertise

def get_user_roles(user_id):
    connection = get_db_connection()
    roles = []
    try:
        with connection.cursor() as cursor:
            sql = "SELECT role_id FROM user_role WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            if results:
                roles = [result['role_id'] for result in results]
    except Exception as e:
        print("Exception:", e)
    finally:
        connection.close()
    return roles


@app.route('/update-expert-profile', methods=['GET', 'POST'])
def update_expert_profile():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    user_roles = get_user_roles(user_id)
    
    if 2 not in user_roles:  # Check if Expert role is present
        return "You are not authorized to access this page."

    expertise = get_expertise_for_user(user_id)

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        expertise_ids = request.form.getlist('expertise')
        price = request.form['price']
        years_of_experience = request.form['years_of_experience']
        details = request.form['details']
        place = 'bronze'  # default place, only admin can change it
        
        connection = get_db_connection()  # Opening connection here
        try:
            with connection.cursor() as cursor:
                # Check if expert profile already exists
                sql = "SELECT * FROM expert_profile WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()

                if result:
                    # Update expert profile
                    sql = "UPDATE expert_profile SET years_of_experience = %s, details = %s, price = %s WHERE user_id = %s"
                    cursor.execute(sql, (years_of_experience, details, price, user_id))
                else:
                    # Insert new expert profile
                    sql = "INSERT INTO expert_profile (user_id, years_of_experience, details, price, place) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(sql, (user_id, years_of_experience, details, price, place))
                
                # Update expertise for the expert
                

                connection.commit()
        except Exception as e:
            print("Exception:", e)
        return redirect('/dashboard')

    return render_template('update-expert-profile.html', expertise=expertise)


@app.route('/user_profile/<int:user_id>')
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect('/login')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch user details
            cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
            user = cursor.fetchone()

            # Fetch user expertise
            cursor.execute('''
                SELECT e.name AS expertise
                FROM expertise e
                INNER JOIN user_role ur ON e.expertise_id = ur.expertise_id
                WHERE ur.user_id = %s
                AND ur.role_id = 2;
            ''', (user_id,))
            expertise = [expertise['expertise'] for expertise in cursor.fetchall()]

            cursor.execute("SELECT * FROM credit_card WHERE user_id = %s", (user_id,))
            credit_card_info = cursor.fetchone()

            # Fetch the number of questions answered by the user
            cursor.execute('SELECT COUNT(*) AS num_answers FROM answer WHERE user_id = %s', (user_id,))
            num_answers = cursor.fetchone()['num_answers']

            cursor.execute('SELECT cv_resume_path FROM user2 WHERE user_id = %s', (user_id,))
            cv_path_result = cursor.fetchone()
            cv_resume_path = cv_path_result['cv_resume_path'] if cv_path_result else None
            
    finally:
        connection.close()

    return render_template('user_profile.html', user=user, expertise=expertise, num_answers=num_answers, cv_resume_path=cv_resume_path, credit_card_info=credit_card_info)


def get_expertise_for_user_request(user_id):
    connection = get_db_connection()
    expertise = []
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM expertise WHERE expertise_id IN (SELECT expertise_id FROM user_role WHERE user_id = %s AND role_id=2)"
            cursor.execute(sql, (user_id,))
            expertise = cursor.fetchall()
    except Exception as e:
        print("Exception:", e)
    finally:
        connection.close()
    return expertise
@app.route('/submit-query', methods=['GET', 'POST'])
def submit_query():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    user_roles = get_user_roles(user_id)

    if 1 not in user_roles:  # Check if Request role is present
        return "You are not authorized to access this page."

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        expertise_id = request.form['expertise_id']

        # Assuming get_db_connection() returns a connection that is already opened
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # Insert the new query into the `query` table
                insert_query = "INSERT INTO `query` (`title`, `description`, `Request_user_id`, `expertise_id`) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (title, description, user_id, expertise_id))
                connection.commit()
                new_query_id = cursor.lastrowid

            # Redirect to the expert selection page with the new query's ID
            return redirect(url_for('select_expert', query_id=new_query_id,expertise_id=expertise_id))

        except Exception as e:
            print("Exception:", e)
            connection.rollback()
            return render_template('submit_query.html', error="Failed to submit query.")
        finally:
            connection.close()

    # Get the expertise areas for the dropdown in the form
    expertise = get_expertise_for_user(user_id)
    return render_template('submit_query.html', expertise=expertise)

@app.route('/select-expert/<int:query_id>/<int:expertise_id>', methods=['GET', 'POST'])
def select_expert(query_id, expertise_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    session_user_id = session['user_id']
    
    if request.method == 'POST':
        selected_experts = request.form.getlist('expert_id')
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                for expert_id in selected_experts:
                    # Insert the relationship between the query and the selected experts
                    insert_query_expert = """
                    INSERT INTO `query_expert` (`user_id`, `expert_user_id`, `query_id`)
                    VALUES (%s, %s, %s)
                    """
                    cursor.execute(insert_query_expert, (session_user_id, expert_id, query_id))
                connection.commit()
        except Exception as e:
            print("Exception:", e)
            connection.rollback()
        finally:
            connection.close()
        # Redirect to one-on-one Q&A page (assuming you have a `qa_page` function)
        return redirect(url_for('qa_page', query_id=query_id))

    # Fetch experts based on the query's expertise_id
    experts = get_experts_by_expertise(expertise_id)
    query_details = get_query_details(query_id)
    return render_template('select_expert.html', experts=experts, query_id=query_id,expertise_id=expertise_id,query_details=query_details)

def get_experts_by_expertise(expertise_id):
    connection = get_db_connection()
    experts = []
    try:
        with connection.cursor() as cursor:
            # Select experts who have the specific expertise
            cursor.execute("""
            SELECT u.user_id, u.username
            FROM user_role ur
            JOIN user u ON ur.user_id = u.user_id
            WHERE ur.role_id = 2 AND ur.expertise_id = %s
            """, (expertise_id,))
            experts = cursor.fetchall()
    except Exception as e:
        print("Exception:", e)
    finally:
        connection.close()
    return experts

def get_query_details(query_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch query details from the query table
            cursor.execute('SELECT title, description, created_at, Request_user_id FROM `query` WHERE query_id = %s', (query_id,))
            query_details = cursor.fetchone()
    except Exception as e:
        print("Exception:", e)
        query_details = None
    finally:
        connection.close()
    return query_details

@app.route('/qa-page/<int:query_id>')
def qa_page(query_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    shared_queries = []
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            # Fetch the details of the query
            cursor.execute("""
                SELECT q.title, q.description, q.created_at, q.Request_user_id,u.username as requester_username
                FROM `query` q
                JOIN user u ON q.Request_user_id = u.user_id
                WHERE q.query_id = %s""", (query_id,))
            query_details = cursor.fetchone()

            

            # Fetch the list of experts the query was shared with
            cursor.execute("""
                SELECT u.username, qe.expert_user_id
                FROM `query_expert` qe
                JOIN user u ON qe.expert_user_id = u.user_id
                WHERE qe.query_id = %s""", (query_id,))
            shared_queries = cursor.fetchall()

            

        
    except Exception as e:
        print("Exception:", e)
    finally:
        connection.close()

    return render_template('qa_page.html', query_details=query_details, shared_queries=shared_queries, user_id=user_id, query_id=query_id)

@app.route('/view-answers/<int:query_id>/<int:expert_user_id>')
def view_answers(query_id,expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    query_info = None
    answers_comments = []
    price_negotiations=[]
    expert_price_record=[]

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch the query information
            cursor.execute("""
                SELECT q.title, q.description, q.Request_user_id, q.created_at, q.accepted_answer, u.username AS requester_username
                FROM query q
                JOIN user u ON q.Request_user_id = u.user_id
                WHERE q.query_id = %s
            """, (query_id,))
            query_info = cursor.fetchone()

            # Fetch the answers and include the answer_id
            cursor.execute("""
                SELECT a.answer_id, a.user_id, a.content AS answer_content, a.created_at AS answer_created_at, 
                u.username AS responder_username
                FROM answer a
                JOIN user u ON a.user_id = u.user_id
                WHERE a.query_id = %s
            """, (query_id,))
            answers = cursor.fetchall()

            # Now fetch comments for each answer and combine them
            for answer in answers:
                cursor.execute("""
                    SELECT c.user_id, c.comment_id, c.content AS comment_content, c.created_at AS comment_created_at
                    FROM comment c
                    WHERE c.answer_id = %s
                """, (answer['answer_id'],))
                comments = cursor.fetchall()
                answer['comments'] = comments
                
                
            answers_comments = answers

            cursor.execute(
                "SELECT * FROM  query_expert WHERE accepted_answer = 0 AND  query_id = %s AND expert_user_id = %s",
                (query_id, expert_user_id)
            )
            expert_answers= cursor.fetchone()

            cursor.execute("""
                SELECT negotiation_id, negotiated_price
                FROM price_negotiation
                WHERE query_id = %s AND is_approved = 0
            """, (query_id,))
            price_negotiations = cursor.fetchall()

            cursor.execute(
                "SELECT rating, message FROM rating WHERE expert_user_id = %s AND query_id = %s",
                (expert_user_id, query_id)
            )
            expert_rating = cursor.fetchone()

            cursor.execute(
                "SELECT price FROM expert_price WHERE query_id = %s AND expert_user_id = %s",
                (query_id, expert_user_id)
            )
            expert_price_record = cursor.fetchone()
            if expert_price_record:
                expert_price_record = expert_price_record['price']


    except Exception as e:
        print("Exception occurred:", e)
    finally:
        connection.close()

    

    return render_template('view_answers.html', 
                           query_info=query_info,
                           price_negotiations=price_negotiations, 
                           answers_comments=answers_comments, 
                           user_id=user_id, 
                           expert_rating=expert_rating,
                           expert_price_record=expert_price_record,
                           expert_answers=expert_answers,
                           query_id=query_id,expert_user_id=expert_user_id)


@app.route('/submit_rating_feedback/<int:query_id>/<int:expert_user_id>', methods=['POST'])
def submit_rating_feedback(query_id, expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    rating = int(request.form['rating'])
    message = request.form['feedback']

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the rating for this query and expert already exists
            cursor.execute(
                "SELECT * FROM rating WHERE query_id = %s AND expert_user_id = %s",
                (query_id, expert_user_id)
            )
            existing_rating = cursor.fetchone()

            if existing_rating:
                # Update existing rating and feedback
                cursor.execute(
                    "UPDATE rating SET rating = %s, message = %s WHERE query_id = %s AND expert_user_id = %s",
                    (rating, message, query_id, expert_user_id)
                )
            else:
                # Insert new rating and feedback
                cursor.execute(
                    "INSERT INTO rating (expert_user_id, request_user_id, query_id, rating, message) VALUES (%s, %s, %s, %s, %s)",
                    (expert_user_id, user_id, query_id, rating, message)
                )

            connection.commit()

    except Exception as e:
        print("Exception occurred:", e)
        connection.rollback()
    finally:
        connection.close()

    return redirect(url_for('view_answers', query_id=query_id, expert_user_id=expert_user_id))


@app.route('/accept_answer/<int:query_id>/<int:expert_user_id>', methods=['POST'])
def accept_answer(query_id, expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    expert_price_record=[]

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT Request_user_id FROM query WHERE query_id = %s", (query_id,))
            requested_user_id = cursor.fetchone()['Request_user_id']

            cursor.execute(
                "SELECT price FROM expert_price WHERE query_id = %s AND expert_user_id = %s",
                (query_id, expert_user_id)
            )
            expert_price_record = cursor.fetchone()
            if expert_price_record:
                expert_price_record = expert_price_record['price']
            # Set accepted_answer to 1 in query table
            cursor.execute(
                "UPDATE query SET accepted_answer = 1 WHERE query_id = %s",
                (query_id,)
            )

            # Update accepted_answer to 1 in query_expert table
            cursor.execute(
                "UPDATE query_expert SET accepted_answer = 1 WHERE query_id = %s AND expert_user_id = %s",
                (query_id, expert_user_id)
            )

            connection.commit()

            # Check if the expert has already answered 20 questions
            cursor.execute("SELECT COUNT(*) AS num_answers FROM query_expert WHERE expert_user_id = %s AND accepted_answer = 1", (expert_user_id,))
            num_answers = cursor.fetchone()['num_answers']

            # Upgrade the expert's place if they have answered 20 questions
            if num_answers >= 20:
                cursor.execute(
                    "UPDATE expert_profile SET place = CASE WHEN place = 'bronze' THEN 'silver' WHEN place = 'silver' THEN 'gold' WHEN place = 'gold' THEN 'platinum' ELSE 'platinum' END WHERE user_id = %s",
                    (expert_user_id,)
                )
                connection.commit()

            # Notify admin that the answer has been accepted
            cursor.execute(
                "INSERT INTO admin_notification (user_id, admin_id, message) VALUES (%s, 1, 'Query %s has an accepted answer by user %s by price %s')",
                (requested_user_id, query_id, expert_user_id,expert_price_record)
            )
            connection.commit()

    except Exception as e:
        connection.rollback()
        print("Error in accept_answer:", e)
    finally:
        connection.close()

    return redirect(f'/view-answers/{query_id}/{expert_user_id}')

@app.route('/reject_answer/<int:query_id>/<int:expert_user_id>', methods=['POST'])
def reject_answer(query_id, expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT Request_user_id FROM query WHERE query_id = %s", (query_id,))
            requested_user_id = cursor.fetchone()['Request_user_id']

            # Set accepted_answer to 2 in query_expert table
            cursor.execute(
                "UPDATE query_expert SET accepted_answer = 2 WHERE query_id = %s AND expert_user_id = %s",
                (query_id, expert_user_id)
            )
            connection.commit()

    except Exception as e:
        connection.rollback()
        print("Error in reject_answer:", e)
    finally:
        connection.close()

    return redirect(f'/view-answers/{query_id}/{expert_user_id}')


@app.route('/set_price/<int:query_id>/<int:expert_user_id>', methods=['GET', 'POST'])
def set_price(query_id, expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    requested_user_id = None

    # Get requested_user_id from the query table
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT Request_user_id FROM query WHERE query_id = %s", (query_id,))
            requested_user_id = cursor.fetchone()['Request_user_id']

            if request.method == 'POST':
                price = float(request.form['price'])

                cursor.execute("SELECT place FROM expert_profile WHERE user_id = %s", (expert_user_id,))
                place = cursor.fetchone()['place']

                # Calculate price range based on expert's place
                if place == 'bronze':
                    if not (1 <= price <= 30):
                        return "Price should be between 1 and 30 for Bronze experts."
                elif place == 'silver':
                    if not (31 <= price <= 60):
                        return "Price should be between 31 and 60 for Silver experts."
                elif place == 'gold':
                    if not (61 <= price <= 90):
                        return "Price should be between 61 and 90 for Gold experts."
                elif place == 'platinum':
                    if not (91 <= price <= 120):
                        return "Price should be between 91 and 120 for Platinum experts."

                cursor.execute("SELECT * FROM expert_price WHERE query_id = %s AND expert_user_id = %s", (query_id, expert_user_id))
                existing_price = cursor.fetchone()

                if existing_price:
                    # Update existing price
                    cursor.execute("UPDATE expert_price SET price = %s WHERE query_id = %s AND expert_user_id = %s", (price, query_id, expert_user_id))
                else:
                    # Insert or update price in the expert_price table
                    cursor.execute(
                        "INSERT INTO expert_price (query_id, expert_user_id, requested_user_id, price) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE price = VALUES(price)",
                        (query_id, expert_user_id, requested_user_id, price)
                    )
                connection.commit()
    except Exception as e:
        connection.rollback()
        print("Error in set_price:", e)
    finally:
        connection.close()

    if request.method == 'POST':
        return redirect(f'/view-answers/{query_id}/{expert_user_id}')

    return render_template('set_price.html', query_id=query_id, expert_user_id=expert_user_id, requested_user_id=requested_user_id, user_id=user_id)

@app.route('/negotiate_price/<int:query_id>/<int:expert_user_id>', methods=['GET', 'POST'])
def negotiate_price(query_id, expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    requested_user_id = None

    # Get requested_user_id from the query table
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT Request_user_id FROM query WHERE query_id = %s", (query_id,))
            requested_user_id = cursor.fetchone()['Request_user_id']

            if request.method == 'POST':
                negotiated_price = float(request.form['negotiated_price'])

                cursor.execute("SELECT place FROM expert_profile WHERE user_id = %s", (expert_user_id,))
                place = cursor.fetchone()['place']

                # Calculate price range based on expert's place
                if place == 'bronze':
                    if not (1 <= negotiated_price <= 30):
                        return "Price should be between 1 and 30 for Bronze experts."
                elif place == 'silver':
                    if not (31 <= negotiated_price <= 60):
                        return "Price should be between 31 and 60 for Silver experts."
                elif place == 'gold':
                    if not (61 <= negotiated_price <= 90):
                        return "Price should be between 61 and 90 for Gold experts."
                elif place == 'platinum':
                    if not (91 <= negotiated_price <= 120):
                        return "Price should be between 91 and 120 for Platinum experts."

                # Insert or update price negotiation
                cursor.execute(
                    "INSERT INTO price_negotiation (query_id, requested_user_id, negotiated_price) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE negotiated_price = VALUES(negotiated_price)",
                    (query_id, requested_user_id, negotiated_price)
                )
                connection.commit()

                return redirect(f'/view-answers/{query_id}/{expert_user_id}')

    except Exception as e:
        print("Error in negotiate_price:", e)
    finally:
        connection.close()

    return render_template('negotiate_price.html', query_id=query_id, expert_user_id=expert_user_id)




@app.route('/approve_price/<int:query_id>/<int:expert_user_id>', methods=['GET', 'POST'])
def approve_price(query_id,expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    connection = get_db_connection()
    if request.method == 'POST':
        negotiation_id = int(request.form['negotiation_id'])

        try:
            with connection.cursor() as cursor:
                # Approve the negotiation
                cursor.execute(
                    "UPDATE price_negotiation SET is_approved = 1 WHERE negotiation_id = %s",
                    (negotiation_id,)
                )

                # Update the expert price
                cursor.execute(
                    "SELECT negotiated_price FROM price_negotiation WHERE negotiation_id = %s",
                    (negotiation_id,)
                )
                approved_price = cursor.fetchone()['negotiated_price']

                cursor.execute(
                    "UPDATE expert_price SET price = %s WHERE query_id = %s AND expert_user_id = %s",
                    (approved_price, query_id, expert_user_id)
                )
                connection.commit()
        except Exception as e:
            connection.rollback()
            print("Error in approve_price:", e)
        finally:
            connection.close()

        return redirect(f'/view-answers/{query_id}/{expert_user_id}')

    # Fetch all price negotiations for approval
    price_negotiations = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM price_negotiation WHERE query_id = %s AND is_approved = 0",
                (query_id,)
            )
            price_negotiations = cursor.fetchall()
    except Exception as e:
        print("Error fetching price_negotiations:", e)

    return render_template('view_answers.html', price_negotiations=price_negotiations, query_id=query_id, expert_user_id=expert_user_id,user_id=user_id)


@app.route('/post_answer/<int:query_id><int:expert_user_id>', methods=['POST'])
def post_answer(query_id,expert_user_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    content = request.form['content']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert the answer into the `answer` table
            sql = "INSERT INTO `answer` (`query_id`, `user_id`, `content`) VALUES (%s, %s, %s)"
            cursor.execute(sql, (query_id, user_id, content))
            connection.commit()
            answer_id= cursor.lastrowid
    except Exception as e:
        print("Exception:", e)
        return render_template('view_answers.html', error="Failed to post answer.")
    finally:
        connection.close()
    
    return redirect(url_for('view_answers', query_id=query_id, answer_id=answer_id,expert_user_id=expert_user_id))


@app.route('/post_comment/<int:answer_id>/<int:query_id>', methods=['POST'])
def post_comment(answer_id , query_id ):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    content = request.form['comment_content']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert the comment into the `comment` table
            sql = "INSERT INTO `comment` (`answer_id`, `user_id`, `content`) VALUES (%s, %s, %s)"
            cursor.execute(sql, (answer_id, user_id, content))
            connection.commit()
    except Exception as e:
        print("Exception:", e)
        return render_template('view_answers.html', error="Failed to post comment.")
    finally:
        connection.close()
    
    # Redirect back to the answer view page, you may need to pass the query_id to this URL
    return redirect(url_for('view_answers', query_id=query_id)) # assuming you have the query_id


from flask import render_template

# # Define error handler for 400 Bad Request
# @app.errorhandler(400)
# def bad_request_error(error):
#     return render_template('error.html', error="400 - Bad Request"), 400

# # Define error handler for 401 Unauthorized
# @app.errorhandler(401)
# def unauthorized_error(error):
#     return render_template('error.html', error="401 - Unauthorized"), 401

# # Define error handler for 403 Forbidden
# @app.errorhandler(403)
# def forbidden_error(error):
#     return render_template('error.html', error="403 - Forbidden"), 403

# # Define error handler for 404 Not Found
# @app.errorhandler(404)
# def page_not_found_error(error):
#     return render_template('error.html', error="404 - Page Not Found"), 404

# # Define error handler for 405 Method Not Allowed
# @app.errorhandler(405)
# def method_not_allowed_error(error):
#     return render_template('error.html', error="405 - Method Not Allowed"), 405

# # Define error handler for 500 Internal Server Error
# @app.errorhandler(500)
# def internal_server_error(error):
#     return render_template('error.html', error="500 - Internal Server Error"), 500

# # Define error handler for 502 Bad Gateway
# @app.errorhandler(502)
# def bad_gateway_error(error):
#     return render_template('error.html', error="502 - Bad Gateway"), 502

# # Define error handler for 503 Service Unavailable
# @app.errorhandler(503)
# def service_unavailable_error(error):
#     return render_template('error.html', error="503 - Service Unavailable"), 503

# # Define error handler for 504 Gateway Timeout
# @app.errorhandler(504)
# def gateway_timeout_error(error):
#     return render_template('error.html', error="504 - Gateway Timeout"), 504

@app.route('/search', methods=['GET'])
def search():
    print("Search function called.")

    search_query = request.args.get('search_query', '')  # Get the search query from the form, default to empty string if not found
    print("Received search query:", search_query)  # Add this line to check if the search query is received correctly

    # Perform search in queries, answers, comments, and expertise tags
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Search in queries
            query_sql = "SELECT * FROM `query` WHERE `title` LIKE %s OR `description` LIKE %s"
            cursor.execute(query_sql, ('%' + search_query + '%', '%' + search_query + '%'))
            queries = cursor.fetchall()
            print("Queries found: ", queries)  # Add this line to check if queries are found

            # Search in answers
            answer_sql = "SELECT a.*, q.query_id, q.title AS question_title FROM `answer` a JOIN `query` q ON a.query_id = q.query_id WHERE a.content LIKE %s"
            cursor.execute(answer_sql, ('%' + search_query + '%',))
            answers = cursor.fetchall()
            print("Answers found: ", answers)  # Add this line to check if answers are found

            # Search in comments
            comment_sql = "SELECT c.*,q.query_id, a.content AS answer_content, q.title AS question_title FROM `comment` c JOIN `answer` a ON c.answer_id = a.answer_id JOIN `query` q ON a.query_id = q.query_id WHERE c.content LIKE %s"
            cursor.execute(comment_sql, ('%' + search_query + '%',))
            comments = cursor.fetchall()
            print("Comments found: ", comments)  # Add this line to check if comments are found

            # Search in expertise tags
            expertise_sql = "SELECT * FROM `expertise` WHERE `name` LIKE %s"
            cursor.execute(expertise_sql, ('%' + search_query + '%',))
            expertise_tags = cursor.fetchall()
            print("Expertise tags found: ", expertise_tags)  # Add this line to check if expertise tags are found

    except Exception as e:
        return render_template('search.html', error="An error occurred during search: {}".format(e))
    finally:
        connection.close()

    # If no results are found for all types
    if not queries and not answers and not comments and not expertise_tags:
        return render_template('search.html', error="No results found.", search_query=search_query)

    # If results are found for any type
    return render_template('search.html', queries=queries, answers=answers, comments=comments, tags=expertise_tags, search_query=search_query)


from flask import request, session, redirect, url_for, render_template

@app.route('/delete-comment/<int:comment_id>/<int:query_id>', methods=['POST'])
def delete_comment(comment_id, query_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the user is the owner of the comment
            cursor.execute("SELECT user_id FROM comment WHERE comment_id = %s", (comment_id,))
            comment_owner = cursor.fetchone()

            if comment_owner and comment_owner['user_id'] == user_id:
                # Delete the comment from the `comment` table
                cursor.execute("DELETE FROM comment WHERE comment_id = %s", (comment_id,))
                connection.commit()
    except Exception as e:
        print("Exception:", e)
        return redirect(url_for('view_answers', query_id=query_id))
    finally:
        connection.close()
    
    return redirect(url_for('view_answers', query_id=query_id))

@app.route('/update-comment/<int:comment_id>/<int:query_id>', methods=['POST'])
def update_comment(comment_id, query_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    new_content = request.form['new_comment_content']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the user is the owner of the comment
            cursor.execute("SELECT user_id FROM comment WHERE comment_id = %s", (comment_id,))
            comment_owner = cursor.fetchone()

            if comment_owner and comment_owner['user_id'] == user_id:
                # Update the comment in the `comment` table
                cursor.execute("UPDATE comment SET content = %s WHERE comment_id = %s", (new_content, comment_id))
                connection.commit()
    except Exception as e:
        print("Exception:", e)
        return redirect(url_for('view_answers', query_id=query_id))
    finally:
        connection.close()
    
    return redirect(url_for('view_answers', query_id=query_id))




from flask import request, redirect, url_for

@app.route('/delete_answer/<int:answer_id>/<int:query_id>', methods=['POST'])
def delete_answer(answer_id, query_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the user is the owner of the answer
            cursor.execute("SELECT user_id FROM answer WHERE answer_id = %s", (answer_id,))
            result = cursor.fetchone()
            if not result or result['user_id'] != user_id:
                # If the user is not the owner, return unauthorized error
                return render_template('error.html', error="401 - Unauthorized"), 401

            # Delete comments associated with the answer
            cursor.execute("DELETE FROM comment WHERE answer_id = %s", (answer_id,))
            
            # Delete the answer
            cursor.execute("DELETE FROM answer WHERE answer_id = %s", (answer_id,))
            connection.commit()
    except Exception as e:
        print("Exception:", e)
        return render_template('error.html', error="Failed to delete answer.")
    finally:
        connection.close()

    # Redirect back to the answer view page
    return redirect(url_for('view_answers', query_id=query_id))

@app.route('/update_answer/<int:answer_id>/<int:query_id>', methods=['POST'])
def update_answer(answer_id, query_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    new_content = request.form['new_content']
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the user is the owner of the answer
            cursor.execute("SELECT user_id FROM answer WHERE answer_id = %s", (answer_id,))
            result = cursor.fetchone()
            if not result or result['user_id'] != user_id:
                # If the user is not the owner, return unauthorized error
                return render_template('error.html', error="401 - Unauthorized"), 401

            # Update the answer content
            cursor.execute("UPDATE answer SET content = %s WHERE answer_id = %s", (new_content, answer_id))
            connection.commit()
    except Exception as e:
        print("Exception:", e)
        return render_template('error.html', error="Failed to update answer.")
    finally:
        connection.close()

    # Redirect back to the answer view page
    return redirect(url_for('view_answers', query_id=query_id))

@app.route('/delete_question/<int:query_id>', methods=['POST'])
def delete_question(query_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    
    connection = get_db_connection()
   
    with connection.cursor() as cursor:
            # Check if the user is the owner of the question
            cursor.execute("SELECT Request_user_id FROM query WHERE query_id = %s", (query_id,))
            result = cursor.fetchone()
            if not result or result['Request_user_id'] != user_id:
                # If the user is not the owner, return unauthorized error
                return render_template('error.html', error="401 - Unauthorized"), 401

            # Delete associated answers
            cursor.execute("DELETE FROM comment WHERE answer_id IN (SELECT answer_id FROM answer WHERE query_id = %s)", (query_id,))
            cursor.execute("DELETE FROM answer WHERE query_id = %s", (query_id,))
            # Delete associated comments
            
            # Delete associated expertise prices
            cursor.execute("DELETE FROM expert_price WHERE query_id = %s", (query_id,))
            # Delete associated query_expert records
            cursor.execute("DELETE FROM query_expert WHERE query_id = %s", (query_id,))
            # Delete the question
            cursor.execute("DELETE FROM query WHERE query_id = %s", (query_id,))
            connection.commit()
    
    

    # Redirect back to the home page or any appropriate page
    return redirect(url_for('dashboard'))
@app.route('/update_question/<int:query_id>', methods=['POST'])
def update_question(query_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    title = request.form['title']
    description = request.form['description']
    
    
    connection = get_db_connection()
    
    with connection.cursor() as cursor:
            # Check if the user is the owner of the question
            cursor.execute("SELECT Request_user_id FROM query WHERE query_id = %s", (query_id,))
            result = cursor.fetchone()
            if not result or result['Request_user_id'] != user_id:
                # If the user is not the owner, return unauthorized error
                return render_template('error.html', error="401 - Unauthorized"), 401

            # Update the question details
            cursor.execute("UPDATE query SET title = %s, description = %s  WHERE query_id = %s", 
                           (title, description, query_id))
            connection.commit()
    
   

    # Redirect back to the question view page or any appropriate page
    return redirect(url_for('dashboard', query_id=query_id))

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['password']
        connection = get_db_connection()

        with connection.cursor() as cursor:
            # Update user's password in the database
            cursor.execute('UPDATE user SET password = %s WHERE email = %s', (new_password, email))
            connection.commit()
            return redirect('/login')
    return render_template('forgotpassword.html')
@app.route('/users')
def users():
    user_id = session['user_id']
    
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute('SELECT user_id, first_name, last_name, username  FROM user')
        users = cursor.fetchall()
    connection.close()
    return render_template('users.html', users=users,user_id = user_id)


@app.route('/questions')
def questions():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM query")
        questions = cursor.fetchall()
        for question in questions:
            cursor.execute("SELECT * FROM answer WHERE query_id = %s", (question['query_id'],))
            question['answers'] = cursor.fetchall()
            for answer in question['answers']:
                cursor.execute("SELECT * FROM comment WHERE answer_id = %s", (answer['answer_id'],))
                answer['comments'] = cursor.fetchall()
    connection.close()
    return render_template('question.html', questions=questions)

@app.route('/expertise')
def expertise():
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM expertise")
        expertise = cursor.fetchall()
    connection.close()
    return render_template('expertise.html', expertise=expertise)

@app.route('/expertise/<int:expertise_id>')
def expertise_questions(expertise_id):
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM query WHERE expertise_id = %s", (expertise_id,))
        questions = cursor.fetchall()
        for question in questions:
            cursor.execute("SELECT * FROM answer WHERE query_id = %s", (question['query_id'],))
            question['answers'] = cursor.fetchall()
            for answer in question['answers']:
                cursor.execute("SELECT * FROM comment WHERE answer_id = %s", (answer['answer_id'],))
                answer['comments'] = cursor.fetchall()
    connection.close()
    return render_template('expertise_question.html', questions=questions)

@app.route('/report/query/<int:query_id>', methods=['POST'])
def report_query(query_id):
    user_id = session.get('user_id')  # The ID of the user who is reporting
    if not user_id:
        return redirect('/login')  # Redirect to login if the user is not logged in

    reason = request.form.get('reason')  # Get the reason for the report from a form
    requested_user_id = request.form.get('requested_user_id')  # Get the ID of the user who asked the query
    expert_user_id = request.form.get('expert_user_id')  # Get the ID of the expert involved in the query

    # Logic to handle the report
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO reports (requested_user_id, expert_user_id, reported_user_id, query_id, reason) 
                VALUES (%s, %s, %s, %s, %s)
            """, (requested_user_id, expert_user_id, user_id, query_id, reason))
            connection.commit()
    except Exception as e:
        print("Exception occurred:", e)
        return render_template('error.html', error=str(e)), 500
    finally:
        connection.close()
    
    return redirect(url_for('view_answers', query_id=query_id, expert_user_id=expert_user_id))

from datetime import datetime
from dateutil.relativedelta import relativedelta



@app.route('/service')
def service():
    if 'user_id' not in session:
        return redirect('/login')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM expertise")
            expertise_areas = cursor.fetchall()
    except Exception as e:
        print("Exception:", e)
        expertise_areas = []
    finally:
        connection.close()

    return render_template('service.html', expertise_areas=expertise_areas)

@app.route('/tools/<int:expertise_id>')
def tools(expertise_id):
    if 'user_id' not in session:
        return redirect('/login')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM expert_tools WHERE expertise_id = %s", (expertise_id,))
            tools = cursor.fetchall()
    except Exception as e:
        print("Exception:", e)
        tools = []
    finally:
        connection.close()

    return render_template('tools.html', tools=tools)

from flask import request

@app.route('/feedback')
def feedback():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('feedback.html')


from flask import request, redirect, render_template
from datetime import datetime

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    feedback_text = request.form.get('feedback_text')
    rating = int(request.form.get('rating'))  # Retrieve and convert rating to integer

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO feedback (user_id, feedback_text, rating) VALUES (%s, %s, %s)",
                (user_id, feedback_text, rating)
            )
            connection.commit()
    except Exception as e:
        print("Exception:", e)
        connection.rollback()
        return "An error occurred during feedback submission."
    finally:
        connection.close()

    return redirect('/dashboard')  # Redirect to dashboard after submission

@app.route('/view-feedback')
def view_feedback():
    if 'user_id' not in session:
        return redirect('/login')

    connection = get_db_connection()
    feedbacks = []
    try:
        with connection.cursor() as cursor:
            # Fetch feedback along with user information
            cursor.execute("""
                SELECT f.feedback_text, f.date_submitted, f.rating, u.username
                FROM feedback f
                JOIN user u ON f.user_id = u.user_id
                ORDER BY f.date_submitted DESC  # Order by most recent feedback
            """)
            feedbacks = cursor.fetchall()  # Fetch all feedback
    except Exception as e:
        print("Exception:", e)
    finally:
        connection.close()

    return render_template('feedback_list.html', feedbacks=feedbacks)  # Render the feedback list

@app.route('/add')
def add():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('submit_expertise.html')

@app.route('/submit_expertise', methods=['POST'])
def submit_expertise():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    expertise_name = request.form['expertise_name']

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert into admin_approval for admin review
            cursor.execute(
                "INSERT INTO admin_approval (user_id, expertise_name) VALUES (%s, %s)",
                (user_id, expertise_name)
            )
            connection.commit()
    except Exception as e:
        print("Error inserting expertise:", e)
        connection.rollback()
    finally:
        connection.close()

    return redirect('/dashboard')

from flask import session, redirect, request, render_template, flash



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print(username)
        print(password)

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    
                    "SELECT admin_id FROM admin WHERE TRIM(username) = %s AND TRIM(password) = %s",

                    (username, password)
                )
                admin = cursor.fetchone()
                print(admin)
                if admin:
                    session['admin_id'] = admin['admin_id']
                    print(1)


                    
                    return redirect('/admin_approvals')
                else:
                    flash("Invalid username or password")
        except Exception as e:
            print("Error during admin login:", e)
        finally:
            connection.close()

    return render_template('admin_login.html')
from flask import Flask, request, render_template, redirect, session
import pymysql
import re
@app.route('/admin_approvals')
def admin_approvals():
    # if 'admin_id' not in session:
    #     return redirect('/admin_login')

    approvals = []
    notifications = []
    price=[]
    admin_credit_card = "1234-5678-9101-1121"  # Default admin credit card number
    admin_credit_card_expiration = "12/25"
    admin_credit_card_cvv = "123"
    credit_card_details = None
    user_details = None
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Fetch pending approvals for admin
            cursor.execute("""
                SELECT aa.admin_approval_id, aa.expertise_name, u.username, aa.approved
                FROM admin_approval aa
                JOIN user u ON aa.user_id = u.user_id
                WHERE aa.approved = 0
            """)
            approvals = cursor.fetchall()

            cursor.execute("""
                SELECT aa.admin_approval_id, aa.expertise_name, u.username, aa.approved
                FROM admin_approval aa
                JOIN user u ON aa.user_id = u.user_id
                WHERE aa.approved = 1
                        
            """)
            approved_expertises = cursor.fetchall()

            
            cursor.execute("""
                SELECT an.message, an.admin_notification_id, an.user_id
                FROM admin_notification an
            """)
            notifications = cursor.fetchall()
            

            # Extract information from the message field in notifications
            notification_details = []
            for notification in notifications:
    # Extract query_id, expert_user_id, price from the message
                message = notification['message']
                pattern = r'Query (\d+) .* answer by user (\d+)(?: by price (.+))?$'
                match = re.search(pattern, message)
                if match:
                    query_id = int(match.group(1))
                    expert_user_id = int(match.group(2))
                    price = float(match.group(3)) if match.group(3) else None
                else:
                    # If no match found, handle accordingly
                    query_id = None
                    expert_user_id = None
                    price = None

                if query_id is not None and expert_user_id is not None:
                    if price is None:
                        # If no price mentioned, set default based on expert's place
                        cursor.execute("""
                            SELECT place
                            FROM expert_profile
                            WHERE user_id = %s
                        """, (expert_user_id,))
                        expert_info = cursor.fetchone()
                        if expert_info:
                            place = expert_info['place']
                            # Set default price based on expert's place
                            if place == 'bronze':
                                price = 15.0
                            elif place == 'silver':
                                price = 45.0
                            elif place == 'gold':
                                price = 75.0
                            elif place == 'platinum':
                                price = 105.0

                    # Fetch additional information using extracted data
                    cursor.execute("""
                        SELECT q.title, q.description, q.Request_user_id, u.username AS requester_username
                        FROM query q
                        JOIN user u ON q.Request_user_id = u.user_id
                        WHERE q.query_id = %s
                    """, (query_id,))
                    query_details = cursor.fetchone()

                    cursor.execute("SELECT * FROM credit_card WHERE user_id = %s", (expert_user_id,))
                    fetched_credit_card = cursor.fetchone()
                    credit_card_details = fetched_credit_card if fetched_credit_card is not None else None
                    print(credit_card_details)
                    # Fetch user details
                    cursor.execute("SELECT * FROM user WHERE user_id = %s", (expert_user_id,))
                    fetched_user_details = cursor.fetchone()
                    user_details = fetched_user_details if fetched_user_details is not None else None
                    print('hi')
                    print(user_details)
                    
                    print('bye')
                    

                    notification_details.append({
                        'admin_notification_id': notification['admin_notification_id'],
                        'message': message,
                        'query_title': query_details['title'],
                        'query_description': query_details['description'],
                        'requester_username': query_details['requester_username'],
                        'price': price,
                        'expert_user_id' : expert_user_id,
                        'user_details': [user_details] if user_details else [],
                        'credit_card_details': [credit_card_details] if credit_card_details else []
                    })



    except Exception as e:
        print("Error fetching approvals:", e)
    finally:
        connection.close()

    return render_template('admin_approvals.html',  credit_card_details =credit_card_details,approvals=approvals,user_details=user_details,approved_expertises=approved_expertises, notifications=notification_details, admin_credit_card=admin_credit_card, admin_credit_card_expiration=admin_credit_card_expiration, admin_credit_card_cvv=admin_credit_card_cvv)

@app.route('/approve_expertise', methods=['POST'])
def approve_expertise():
    if 'admin_id' not in session:
        return redirect('/admin_login')

    admin_approval_id = request.form['admin_approval_id']

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Get the expertise_name from admin_approval
            cursor.execute(
                "SELECT expertise_name FROM admin_approval WHERE admin_approval_id = %s",
                (admin_approval_id,)
            )
            expertise_name = cursor.fetchone()['expertise_name']

            # Insert into expertise table
            cursor.execute(
                "INSERT INTO expertise (name) VALUES (%s)",
                (expertise_name,)
            )

            # Mark as approved
            cursor.execute(
                "UPDATE admin_approval SET approved = 1 WHERE admin_approval_id = %s",
                (admin_approval_id,)
            )
            
            connection.commit()
    except Exception as e:
        print("Error approving expertise:", e)
        connection.rollback()
    finally:
        connection.close()

    return redirect('/admin_approvals')

from flask import Flask, request, render_template, redirect, session
import os
import uuid
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Get the base directory of your Flask application
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads/cv_resumes')  # Define the upload folder path
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist



# Directory to store uploaded CVs/resumes

 # Ensure the folder exists
@app.route('/upload_cv', methods=['POST'])
def upload_cv():
    if 'user_id' not in session:
        return redirect('/login')

    file = request.files.get('cv_resume')
    if file:
        user_id = session['user_id']
        
        # Retrieve username from user table
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT username FROM user WHERE user_id = %s", (user_id,))
                username = cursor.fetchone()['username']
        except Exception as e:
            print("Error:", e)
            connection.close()
            return redirect('/error_page')  # Redirect to an error page or handle the error appropriately
        
        # Construct filename
        filename = username + '_cv' + os.path.splitext(file.filename)[-1]
        # In the upload_cv function, save the relative path to the database
        file_path = 'uploads/cv_resumes/' + filename  # Store relative path in the database

        file.save(file_path)  # Save the file

        # Insert file path into user2 table
        try:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO user2 (user_id, cv_resume_path) VALUES (%s, %s)", (user_id, file_path))
                connection.commit()
        except Exception as e:
            print("Error:", e)
            connection.rollback()
        finally:
            connection.close()

    return redirect(f'/user_profile/{user_id}')
from flask import send_from_directory

@app.route('/serve_cv/<path:filename>')
def serve_cv(filename):
    return send_from_directory(UPLOAD_FOLDER, filename) 

from flask import Flask, request, render_template, redirect, session
import datetime
from dateutil.relativedelta import relativedelta
import pymysql



@app.route('/filter_question', methods=['GET', 'POST'])
def filter_question():
    if 'user_id' not in session:
        return redirect('/login')

    # Default filter by day
    filter_by = 'day'
    results = []

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            if request.method == 'POST':
                filter_by = request.form['filter_by']

            # Get the current date
            now = datetime.datetime.now()

            if filter_by == 'day':
                start_time = now - datetime.timedelta(days=1)

                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at
                    FROM query q
                    WHERE q.created_at >= %s
                    ORDER BY q.created_at DESC
                """, (start_time,))
                results = cursor.fetchall()

            elif filter_by == 'week':
                start_time = now - datetime.timedelta(weeks=1)

                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at
                    FROM query q
                    WHERE q.created_at >= %s
                    ORDER BY q.created_at DESC
                """, (start_time,))
                results = cursor.fetchall()

            elif filter_by == 'month':
                start_time = now - relativedelta(months=1)

                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at
                    FROM query q
                    WHERE q.created_at >= %s
                    ORDER BY q.created_at DESC
                """, (start_time,))
                results = cursor.fetchall()
            elif filter_by == 'year':
                start_time = now - relativedelta(years=1)

                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at
                    FROM query q
                    WHERE q.created_at >= %s
                    ORDER BY q.created_at DESC
                """, (start_time,))
                results = cursor.fetchall()

            elif filter_by == 'most_rated':
                # Fetch queries with the most ratings
                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at, 
                    COUNT(r.rating_id) AS rating_count
                    FROM query q
                    LEFT JOIN rating r ON q.query_id = r.query_id
                    GROUP BY q.query_id
                    ORDER BY rating_count DESC
                """)
                results = cursor.fetchall()
            elif filter_by == 'great_place':
                # Fetch queries with experts in descending place order
                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at,
                    ep.place
                    FROM query q
                    JOIN query_expert qe ON q.query_id = qe.query_id
                    JOIN expert_profile ep ON qe.expert_user_id = ep.user_id
                    ORDER BY FIELD(ep.place, 'platinum', 'gold', 'silver', 'bronze')
                """)
                results = cursor.fetchall()
            elif filter_by == 'high_price':
                # Fetch queries with the highest price in the expert_price table
                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at,
                    ep.price
                    FROM query q
                    JOIN expert_price ep ON q.query_id = ep.query_id
                    ORDER BY ep.price DESC
                """)
                results = cursor.fetchall()
            else:
                # Fetch queries created within the specified time frame
                cursor.execute("""
                    SELECT q.query_id, q.title, q.description, q.Request_user_id, q.created_at
                    FROM query q
                    WHERE q.created_at >= %s
                    ORDER BY q.created_at DESC
                """, (start_time,))
                results = cursor.fetchall()

                # Fetch user credit card details
                
# Pass credit_card_details to the template

    except Exception as e:
        print("Error fetching filtered questions:", e)
    finally:
        connection.close()

    return render_template('filter_question.html', filter_by=filter_by, results=results)
from paypalrestsdk import Payment, configure 
from flask import redirect

@app.route('/payment_page/<int:admin_notification_id>', methods=['GET'])
def payment_page(admin_notification_id):
    if 'admin_id' not in session:
        return redirect('/admin_login')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Retrieve notification details
            cursor.execute("""
                SELECT an.admin_notification_id, an.message
                FROM admin_notification an
                WHERE an.admin_notification_id = %s
            """, (admin_notification_id,))
            notification = cursor.fetchone()

            # Extract relevant data from the notification message
            message = notification['message']
            pattern = r'Query (\d+) .* answer by user (\d+)(?: by price (.+))?$'
            match = re.search(pattern, message)
            if match:
                    query_id = int(match.group(1))
                    expert_user_id = int(match.group(2))
                    price = float(match.group(3)) if match.group(3) else None

                    cursor.execute("SELECT * FROM credit_card WHERE user_id = %s", (expert_user_id,))
                    credit_card_info = cursor.fetchone()
                    if not credit_card_info:
                      return "Credit card details not found", 404
                
                # Ensure w e have all necessary data
                
            else:
                    # If no match found, handle accordingly
                    query_id = None
                    expert_user_id = None
                    price = None

            if query_id is not None and expert_user_id is not None:
                    if price is None:
                        # If no price mentioned, set default based on expert's place
                        cursor.execute("""
                            SELECT place
                            FROM expert_profile
                            WHERE user_id = %s
                        """, (expert_user_id,))
                        expert_info = cursor.fetchone()
                        if expert_info:
                            place = expert_info['place']
                            # Set default price based on expert's place
                            if place == 'bronze':
                                price = 15.0
                            elif place == 'silver':
                                price = 45.0
                            elif place == 'gold':
                                price = 75.0
                            elif place == 'platinum':
                                price = 105.0

            if query_id and expert_user_id:
                return render_template('payment_page.html', credit_card=credit_card_info,  expert_user_id=expert_user_id, query_id=query_id,admin_credit_card="1234-5678-9101-1121", admin_credit_card_expiration="12/25", admin_credit_card_cvv="123", price=price)

    finally:
        connection.close()

    return redirect('/admin_approvals')

@app.route('/update_credit_card', methods=['POST'])
def update_credit_card():
    if 'user_id' not in session:
        return redirect('/login')  # Redirect to login if not logged in

    user_id = session['user_id']  # Get the logged-in user's ID
    card_number = request.form['card_number']
    expiration_date = request.form['expiration_date']
    expiration_date = expiration_date[:2] + '/' + expiration_date[2:]
    print(expiration_date)
    cvv = request.form['cvv']
    print(cvv)

    # Update credit card information in the database
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Check if the user already has a credit card record
            cursor.execute("""
                SELECT * FROM credit_card
                WHERE user_id = %s
            """, (user_id,))
            existing_card = cursor.fetchone()

            if existing_card:
                # Update existing credit card record
               # Update existing credit card record
                cursor.execute("""
                    UPDATE credit_card
                    SET card_number = %s, expiration_date = STR_TO_DATE(CONCAT('01/', %s), '%%d/%%m/%%y'), cvv = %s
                    WHERE user_id = %s
                """, (card_number, expiration_date, cvv, user_id))
                print(expiration_date)

            else:
            # Insert a new credit card record if none exists
                cursor.execute("""
                    INSERT INTO credit_card (user_id, card_number, expiration_date, cvv)
                    VALUES (%s, %s, STR_TO_DATE(CONCAT('01/', %s), '%%d/%%m/%%y'), %s)
                """, (user_id, card_number, expiration_date, cvv))


            connection.commit()  # Commit the changes to the database

    except Exception as e:
        print("Error updating credit card:", e)  # Log any error
        connection.rollback()  # Rollback changes on error

    finally:
        connection.close()  # Close the database connection

    return redirect(f'/user_profile/{user_id}')  # Redirect to the user profile page


@app.route('/pay', methods=['POST'])
def pay():
    expert_user_id = request.form.get("expert_user_id")
    price = request.form.get("price")
    query_id= request.form.get("query_id")

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Insert payment record
            cursor.execute("""
                INSERT INTO payments (query_id, expert_user_id, price, status)
                VALUES (%s, %s, %s, 'COMPLETED')
            """, (query_id, expert_user_id, price))
            connection.commit()

            return redirect('/admin_approvals', "Payment Successful")
    except Exception as e:
        print("Error processing payment:", e)
        connection.rollback()
        return "Payment Failed", 400
    finally:
        connection.close()


if __name__ == "__main__":
    app.run(debug=True,port=8087)
