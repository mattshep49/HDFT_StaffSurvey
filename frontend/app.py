"""
Flask Web Application for HDFT Staff Survey
URL-based survey interface with token validation
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import logging
import os
import json
from datetime import datetime
from functools import wraps

from app.config import Config
from app.token_manager import TokenManager
from app.fabric_connector import FabricLakehouseConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Initialize token manager and Fabric connector
os.makedirs('data', exist_ok=True)
token_manager = TokenManager('data/tokens.db')
fabric_connector = FabricLakehouseConnector()


# ============================================================================
# DECORATORS
# ============================================================================

def require_token(f):
    """Decorator to require valid token in session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get('token') or session.get('token')
        
        if not token:
            return redirect(url_for('invalid_token'))
        
        is_valid, token_data = token_manager.validate_token(token)
        
        if not is_valid:
            return redirect(url_for('invalid_token'))
        
        # Store in session
        session['token'] = token
        session['token_data'] = token_data
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Homepage - redirects to survey entry"""
    return redirect(url_for('enter_survey'))


@app.route('/enter', methods=['GET', 'POST'])
def enter_survey():
    """Survey entry page - user enters their token"""
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        
        if not token:
            return render_template('enter.html', error='Please enter your survey token')
        
        # Validate token
        is_valid, token_data = token_manager.validate_token(token)
        
        if not is_valid:
            logger.warning(f"Invalid token attempted: {token[:8]}...")
            return render_template('enter.html', error='Invalid or expired survey token')
        
        # Store in session and redirect to survey
        session['token'] = token
        session['token_data'] = token_data
        
        if token_data.get('already_submitted'):
            return redirect(url_for('already_submitted'))
        
        return redirect(url_for('survey'))
    
    return render_template('enter.html')


@app.route('/survey')
@require_token
def survey():
    """Main survey page"""
    token_data = session.get('token_data', {})
    
    # Load survey questions
    survey_config = load_survey_questions()
    
    context = {
        'staff_name': token_data.get('staff_name'),
        'department': token_data.get('department'),
        'survey_title': Config.SURVEY_TITLE,
        'survey_description': Config.SURVEY_DESCRIPTION,
        'questions': survey_config.get('questions', []),
        'total_questions': len(survey_config.get('questions', []))
    }
    
    return render_template('survey.html', **context)


@app.route('/api/survey/submit', methods=['POST'])
@require_token
def submit_survey():
    """Submit survey responses"""
    try:
        token = session.get('token')
        token_data = session.get('token_data', {})
        responses = request.get_json()
        
        if not token or not responses:
            return jsonify({'error': 'Invalid request'}), 400
        
        # Store responses (implementation depends on your database)
        response_record = {
            'token_id': token_data.get('token_id'),
            'assignment_number': token_data.get('assignment_number'),
            'staff_id': token_data.get('staff_id'),
            'responses': responses,
            'submitted_at': datetime.now().isoformat()
        }
        
        # Save response to database
        response_id = save_survey_response(response_record)
        
        # Mark token as used
        token_manager.mark_token_used(token, response_id)
        
        # Clear session
        session.clear()
        
        logger.info(f"Survey submitted for assignment {token_data.get('assignment_number')}")
        
        return jsonify({
            'success': True,
            'message': 'Thank you for completing the survey',
            'redirect': url_for('thank_you')
        })
        
    except Exception as e:
        logger.error(f"Error submitting survey: {e}")
        return jsonify({'error': 'Error submitting survey'}), 500


@app.route('/thank-you')
def thank_you():
    """Thank you page after submission"""
    return render_template('thank_you.html', 
                          title='Thank You',
                          message='Your survey response has been recorded. Thank you for your feedback!')


@app.route('/invalid-token')
def invalid_token():
    """Invalid token error page"""
    return render_template('error.html',
                          title='Invalid Token',
                          message='The survey token is invalid or has expired. Please check and try again.'), 400


@app.route('/already-submitted')
def already_submitted():
    """Already submitted message"""
    return render_template('error.html',
                          title='Already Submitted',
                          message='This survey token has already been used. Thank you for your participation!'), 200


@app.route('/admin/stats')
def admin_stats():
    """Admin dashboard - survey statistics (authentication required in production)"""
    stats = token_manager.get_token_stats()
    
    return jsonify({
        'app_name': Config.APP_NAME,
        'survey_open': Config.SURVEY_OPEN,
        'timestamp': datetime.now().isoformat(),
        'statistics': stats
    })


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_survey_questions():
    """Load survey questions from Fabric table"""
    try:
        # Load from Fabric table 'survey_questions'
        questions = fabric_connector.load_survey_questions(table_name='survey_questions')
        
        if questions:
            logger.info(f"Loaded {len(questions)} questions from Fabric")
            return {
                'title': Config.SURVEY_TITLE,
                'questions': questions
            }
        else:
            logger.warning("No questions loaded from Fabric, using defaults")
            return _get_default_survey()
            
    except Exception as e:
        logger.error(f"Error loading survey questions from Fabric: {e}")
        return _get_default_survey()


def _get_default_questions():
    """Return default survey questions"""
    return [
        {"question_id": "Q1", "question_text": "How satisfied are you with your job?", "answer_type": "likert", "answer_options": "[\"Very Dissatisfied\", \"Dissatisfied\", \"Neutral\", \"Satisfied\", \"Very Satisfied\"]", "is_required": True, "section": "Job Satisfaction", "sequence": 1},
        {"question_id": "Q2", "question_text": "Do you have the tools you need to do your job?", "answer_type": "multiple_choice", "answer_options": "[\"Yes\", \"No\"]", "is_required": True, "section": "Resources", "sequence": 2},
        {"question_id": "Q2a", "question_text": "What tools are missing?", "answer_type": "textarea", "answer_options": "[]", "is_required": False, "section": "Resources", "sequence": 3},
    ]

def _get_default_survey():
    """Return default survey structure"""
    return {
        'title': Config.SURVEY_TITLE,
        'questions': _get_default_questions()
    }


def save_survey_response(response_record):
    """Save survey response to Fabric table"""
    try:
        # Save to Fabric table 'survey_responses'
        success = fabric_connector.save_survey_response(
            table_name='survey_responses',
            response_data=response_record
        )
        
        if success:
            logger.info(f"Response saved for assignment {response_record['assignment_number']}")
            # Return a mock ID for local tracking
            return response_record['token_id']
        else:
            raise Exception("Failed to save response to Fabric")
            
    except Exception as e:
        logger.error(f"Error saving survey response: {e}")
        raise


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('error.html',
                          title='Page Not Found',
                          message='The page you are looking for does not exist.'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return render_template('error.html',
                          title='Error',
                          message='An error occurred. Please try again later.'), 500


# ============================================================================
# CLI COMMANDS
# ============================================================================

@app.cli.command()
def init_db():
    """Initialize the database"""
    token_manager._init_db()
    print("Database initialized")


@app.cli.command()
def show_stats():
    """Show survey statistics"""
    stats = token_manager.get_token_stats()
    print(f"\nSurvey Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Create required directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Run app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )
