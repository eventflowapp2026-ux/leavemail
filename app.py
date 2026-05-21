from flask import Flask, render_template, request, jsonify, session
import json
import datetime
import re
import os
from functools import wraps
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'leavemail-secret-key-change-in-production'

# Default templates with HTML formatting
DEFAULT_TEMPLATES = {
    'professional': """<div style="font-family: Arial, sans-serif; max-width: 600px;">
<p>Dear <strong>{recipient_name}</strong>,</p>

<p>Please excuse <strong>{student_name}</strong> from <strong>{student_class}</strong> for leave from <strong>{start_datetime}</strong> to <strong>{end_datetime}</strong>.</p>

<p><strong>Reason for leave:</strong><br>
{reason}</p>

<p>During this leave period, <strong>{parent_name}</strong> will ensure {student_name} catches up on any missed assignments.</p>

<p>Thank you for your understanding.</p>

<p>Sincerely,<br>
<strong>{parent_name}</strong><br>
{parent_phone}</p>
</div>""",

    'casual': """<div style="font-family: 'Segoe UI', sans-serif;">
<p>Hi <strong>{recipient_name}</strong>,</p>

<p><strong>{student_name}</strong> will need to be away from <strong>{start_datetime}</strong> to <strong>{end_datetime}</strong>.</p>

<p><strong>Reason:</strong> {reason}</p>

<p>Thanks for understanding!<br>
<strong>{parent_name}</strong></p>
</div>""",

    'entertaining': """<div style="font-family: 'Comic Sans MS', cursive, sans-serif;">
<p>🎭 <strong>DRAMATIC LEAVE ANNOUNCEMENT</strong> 🎭</p>

<p>Dear <strong>{recipient_name}</strong>,</p>

<p>By royal decree of the <strong>{parent_name}</strong> household, <strong>{student_name}</strong> shall be embarking on a magnificent journey away from academia from <strong>{start_datetime}</strong> until <strong>{end_datetime}</strong>.</p>

<p><strong>The official reason:</strong> {reason}</p>

<p>Fear not! {student_name} shall return with tales to tell and homework completed.</p>

<p>Dramatically yours,<br>
<strong>{parent_name}</strong> ✨</p>
</div>""",

    'custom': """<div style="font-family: Arial, sans-serif;">
<p>To <strong>{recipient_name}</strong>,</p>

<p><strong>Reason:</strong> {reason}</p>

<p><strong>Dates:</strong> {start_datetime} to {end_datetime}</p>

<p>Regards,<br>
<strong>{parent_name}</strong></p>
</div>"""
}

# Email visual themes
EMAIL_THEMES = {
    'default': {
        'name': 'Default',
        'css': 'body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; } strong { color: #4F46E5; }'
    },
    'modern': {
        'name': 'Modern',
        'css': 'body { font-family: "Segoe UI", sans-serif; line-height: 1.6; color: #1a1a2e; } strong { color: #e94560; background: #f0f0f0; padding: 2px 4px; border-radius: 4px; }'
    },
    'elegant': {
        'name': 'Elegant',
        'css': 'body { font-family: Georgia, serif; line-height: 1.8; color: #2c1810; } strong { color: #8b4513; font-style: italic; }'
    },
    'colorful': {
        'name': 'Colorful',
        'css': 'body { font-family: "Comic Neue", cursive; line-height: 1.6; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 15px; } strong { color: #ffd700; }'
    },
    'minimal': {
        'name': 'Minimal',
        'css': 'body { font-family: "Courier New", monospace; line-height: 1.6; color: #000; } strong { text-decoration: underline; }'
    },
    'festive': {
        'name': 'Festive',
        'css': 'body { font-family: "Comic Sans MS", cursive; line-height: 1.6; background: #fff9c4; color: #c62828; padding: 15px; border-left: 5px solid #ffd700; } strong { color: #ff6f00; font-size: 1.1em; }'
    }
}

# Page themes
THEMES = {
    'default': {'name': 'Default', 'css': 'default.css'},
    'christmas': {'name': 'Christmas 🎄', 'css': 'christmas.css'},
    'onam': {'name': 'Onam 🌸', 'css': 'onam.css'},
    'newyear': {'name': 'New Year 🎆', 'css': 'newyear.css'},
    'independence': {'name': 'Independence Day 🇮🇳', 'css': 'independence.css'}
}

def format_datetime(dt_string):
    """Convert ISO datetime to readable format without T"""
    if not dt_string:
        return "Not specified"
    try:
        # Handle both formats with and without microseconds
        dt_string = dt_string.replace('Z', '')
        if 'T' in dt_string:
            dt = datetime.datetime.fromisoformat(dt_string)
            return dt.strftime('%B %d, %Y at %I:%M %p')
        return dt_string
    except:
        return dt_string

@app.route('/')
def index():
    """Main leave request page"""
    return render_template('index.html', themes=THEMES)

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', templates=DEFAULT_TEMPLATES, themes=THEMES)

@app.route('/history')
def history():
    """Leave history page"""
    return render_template('history.html')

@app.route('/api/save-settings', methods=['POST'])
def save_settings():
    """Save user settings to session"""
    data = request.json
    session['settings'] = data
    return jsonify({'status': 'success', 'message': 'Settings saved'})

@app.route('/api/get-settings', methods=['GET'])
def get_settings():
    """Retrieve user settings"""
    settings = session.get('settings', {
        'student_name': '',
        'student_class': '',
        'parent_name': '',
        'parent_phone': '',
        'recipient_name': 'Teacher',
        'recipient_email': '',
        'default_template': 'professional',
        'templates': DEFAULT_TEMPLATES,
        'email_theme': 'default',
        'accessibility': {
            'high_contrast': False,
            'large_text': False,
            'reduced_motion': False
        },
        'security': {
            'lock_type': 'none',
            'pin_code': '',
            'password': '',
            'pattern': ''
        }
    })
    return jsonify(settings)

@app.route('/api/generate-email', methods=['POST'])
def generate_email():
    """Generate email from template and form data"""
    data = request.json
    
    # Get template and email theme
    template_type = data.get('template_type', 'professional')
    custom_template = data.get('custom_template', '')
    email_theme = data.get('email_theme', 'default')
    
    # Use custom template if provided
    if template_type == 'custom' and custom_template:
        template = custom_template
    else:
        templates = session.get('settings', {}).get('templates', DEFAULT_TEMPLATES)
        template = templates.get(template_type, DEFAULT_TEMPLATES['professional'])
    
    # Get email theme CSS
    theme_css = EMAIL_THEMES.get(email_theme, EMAIL_THEMES['default'])['css']
    
    # Format dates nicely (remove T)
    start_raw = data.get('start_datetime', '')
    end_raw = data.get('end_datetime', '')
    start_formatted = format_datetime(start_raw)
    end_formatted = format_datetime(end_raw)
    
    # Calculate duration
    duration = calculate_duration(start_raw, end_raw)
    
    # Prepare placeholders
    placeholders = {
        'student_name': data.get('student_name', ''),
        'student_class': data.get('student_class', ''),
        'parent_name': data.get('parent_name', ''),
        'parent_phone': data.get('parent_phone', ''),
        'recipient_name': data.get('recipient_name', 'Teacher'),
        'start_datetime': start_formatted,
        'end_datetime': end_formatted,
        'reason': data.get('reason', 'Not specified'),
        'leave_duration': duration,
        'current_date': datetime.datetime.now().strftime('%B %d, %Y'),
        'day_of_week': datetime.datetime.now().strftime('%A')
    }
    
    # Replace placeholders
    email_body_html = template
    for key, value in placeholders.items():
        email_body_html = email_body_html.replace(f'{{{key}}}', str(value))
    
    # Wrap with theme CSS
    full_email_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        {theme_css}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .attachment-note {{
            background: #f0f0f0;
            padding: 10px;
            margin-top: 20px;
            border-radius: 8px;
            font-size: 12px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="email-container">
        {email_body_html}</div>
</body>
</html>"""
    
    # Create plain text version
    plain_text_body = email_body_html.replace('<br>', '\n').replace('</p>', '\n\n')
    plain_text_body = plain_text_body.replace('<p>', '').replace('</p>', '')
    plain_text_body = plain_text_body.replace('<strong>', '').replace('</strong>', '')
    plain_text_body = plain_text_body.replace('<div', '').replace('</div>', '')
    plain_text_body = re.sub(r'<[^>]+>', '', plain_text_body)
    plain_text_body = plain_text_body.strip()
    
    # Prepare email subject
    subject = f"Leave Request - {placeholders['student_name']} - {start_formatted[:20] if start_formatted else 'Upcoming'}"
    
    # Prepare mailto link (using plain text for compatibility)
    recipient = data.get('recipient_email', '')
    mailto_link = f"mailto:{recipient}?subject={quote(subject)}&body={quote(plain_text_body)}"
    
    # Save to history
    history_entry = {
        'id': datetime.datetime.now().timestamp(),
        'timestamp': datetime.datetime.now().isoformat(),
        'student': placeholders['student_name'],
        'start': start_formatted,
        'end': end_formatted,
        'reason': placeholders['reason'],
        'subject': subject,
        'body_html': full_email_html,
        'body_plain': plain_text_body,
        'recipient': recipient,
        'email_theme': email_theme
    }
    
    history = session.get('history', [])
    history.insert(0, history_entry)
    session['history'] = history[:50]
    
    return jsonify({
        'status': 'success',
        'subject': subject,
        'body_html': full_email_html,
        'body_plain': plain_text_body,
        'mailto_link': mailto_link,
        'history_entry': history_entry
    })

@app.route('/api/get-history', methods=['GET'])
def get_history():
    """Retrieve leave history"""
    history = session.get('history', [])
    return jsonify(history)

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear leave history"""
    session['history'] = []
    return jsonify({'status': 'success'})

@app.route('/api/voice-input', methods=['POST'])
def voice_input():
    """Process voice input and extract leave information"""
    data = request.json
    transcript = data.get('transcript', '').lower()
    
    extracted = {
        'reason': '',
        'start_offset': 0,
        'duration_hours': 24,
        'confidence': 'low'
    }
    
    # Keyword extraction
    if 'fever' in transcript or 'sick' in transcript or 'ill' in transcript:
        extracted['reason'] = '🤒 Sick leave - Medical condition'
        extracted['confidence'] = 'high'
    elif 'family' in transcript or 'function' in transcript or 'wedding' in transcript:
        extracted['reason'] = '👨‍👩‍👧 Family function/event'
        extracted['confidence'] = 'high'
    elif 'emergency' in transcript:
        extracted['reason'] = '🚨 Family emergency'
        extracted['confidence'] = 'high'
    elif 'doctor' in transcript or 'appointment' in transcript:
        extracted['reason'] = '🏥 Medical appointment'
        extracted['confidence'] = 'high'
    elif 'travel' in transcript or 'trip' in transcript:
        extracted['reason'] = '✈️ Family travel'
        extracted['confidence'] = 'medium'
    else:
        extracted['reason'] = transcript
    
    # Parse time references
    if 'tomorrow' in transcript:
        extracted['start_offset'] = 1
    elif 'day after' in transcript:
        extracted['start_offset'] = 2
    
    if 'one day' in transcript or '1 day' in transcript:
        extracted['duration_hours'] = 24
    elif 'two days' in transcript or '2 days' in transcript:
        extracted['duration_hours'] = 48
    elif 'three days' in transcript or '3 days' in transcript:
        extracted['duration_hours'] = 72
    
    return jsonify(extracted)

def calculate_duration(start, end):
    """Calculate duration between two datetime strings"""
    if not start or not end:
        return "Not specified"
    
    try:
        start_dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        diff = end_dt - start_dt
        days = diff.days
        hours = diff.seconds // 3600
        
        if days > 0:
            return f"{days} day(s) and {hours} hour(s)"
        else:
            return f"{hours} hour(s)"
    except:
        return "Invalid dates"

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
