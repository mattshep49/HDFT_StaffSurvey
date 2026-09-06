"""
Token Generation and Survey URL Distribution Script
Generate personalized survey URLs for staff members
"""

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict

class SurveyTokenGenerator:
    """Generate tokens and URLs for staff survey distribution"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token
        
        Args:
            length: Token length (default 32 chars)
            
        Returns:
            URL-safe random token
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def create_survey_urls(
        staff_list: List[Dict],
        base_url: str,
        token_expiry_days: int = 90
    ) -> List[Dict]:
        """
        Create personalized survey URLs for staff members
        
        Args:
            staff_list: List of staff dicts with keys:
                - assignment_number: Unique assignment ID
                - staff_id: Employee ID
                - staff_name: Full name
                - email: Email address
                - department: Department
            base_url: Base survey URL (e.g., https://survey.hdft.nhs.uk)
            token_expiry_days: Days until token expires
            
        Returns:
            List of dicts with token info and personalized URLs
        """
        survey_urls = []
        expires_at = datetime.now() + timedelta(days=token_expiry_days)
        
        for staff in staff_list:
            # Generate token
            token = SurveyTokenGenerator.generate_token()
            token_hash = SurveyTokenGenerator.hash_token(token)
            
            # Create personalized URL
            survey_url = f"{base_url}/?token={token}"
            
            survey_urls.append({
                'assignment_number': staff.get('assignment_number'),
                'staff_id': staff.get('staff_id'),
                'staff_name': staff.get('staff_name'),
                'email': staff.get('email'),
                'department': staff.get('department'),
                'token': token,
                'token_hash': token_hash,
                'survey_url': survey_url,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat()
            })
        
        return survey_urls
    
    @staticmethod
    def generate_email_template(
        staff_name: str,
        survey_url: str,
        survey_title: str = "HDFT Staff Survey 2024"
    ) -> Dict[str, str]:
        """
        Generate email template for survey distribution
        
        Args:
            staff_name: Staff member name
            survey_url: Personalized survey URL
            survey_title: Title of survey
            
        Returns:
            Dict with subject and body
        """
        subject = f"Your {survey_title} - Your feedback matters"
        
        body = f"""Dear {staff_name},

We value your feedback and would like to invite you to participate in our staff survey.

Your feedback helps us understand what's working well and where we can improve.

The survey should take approximately 10-15 minutes to complete.

Click here to begin: {survey_url}

This link is unique to you and will expire in 90 days.

Thank you for taking the time to share your views.

Best regards,
Human Resources Team
Harrogate and District NHS Foundation Trust

---
If you experience any technical issues accessing the survey, please contact HR.
"""
        
        return {
            'subject': subject,
            'body': body
        }
    
    @staticmethod
    def export_for_lakehouse(
        survey_urls: List[Dict],
        output_file: str = 'survey_tokens.json'
    ) -> None:
        """
        Export tokens for bulk insert into Lakehouse
        
        Args:
            survey_urls: List of survey URL objects
            output_file: Output JSON file
        """
        # Transform for Lakehouse insert
        tokens_for_insert = []
        
        for item in survey_urls:
            tokens_for_insert.append({
                'token': item['token'],
                'token_hash': item['token_hash'],
                'assignment_number': item['assignment_number'],
                'staff_id': item['staff_id'],
                'staff_name': item['staff_name'],
                'department': item['department'],
                'created_at': item['created_at'],
                'expires_at': item['expires_at'],
                'is_valid': 1,
                'used_at': None,
                'response_id': None
            })
        
        with open(output_file, 'w') as f:
            json.dump(tokens_for_insert, f, indent=2)
        
        print(f"✓ Exported {len(tokens_for_insert)} tokens to {output_file}")
    
    @staticmethod
    def export_for_csv(
        survey_urls: List[Dict],
        output_file: str = 'survey_urls.csv'
    ) -> None:
        """
        Export URLs as CSV for email distribution
        
        Args:
            survey_urls: List of survey URL objects
            output_file: Output CSV file
        """
        import csv
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    'staff_name',
                    'email',
                    'assignment_number',
                    'department',
                    'survey_url'
                ]
            )
            writer.writeheader()
            
            for item in survey_urls:
                writer.writerow({
                    'staff_name': item['staff_name'],
                    'email': item['email'],
                    'assignment_number': item['assignment_number'],
                    'department': item['department'],
                    'survey_url': item['survey_url']
                })
        
        print(f"✓ Exported {len(survey_urls)} URLs to {output_file}")


# Example usage
if __name__ == "__main__":
    # Sample staff list (normally from database)
    sample_staff = [
        {
            'assignment_number': 'ASS-001',
            'staff_id': 'EMP-12345',
            'staff_name': 'John Smith',
            'email': 'john.smith@hdft.nhs.uk',
            'department': 'Clinical'
        },
        {
            'assignment_number': 'ASS-002',
            'staff_id': 'EMP-12346',
            'staff_name': 'Jane Doe',
            'email': 'jane.doe@hdft.nhs.uk',
            'department': 'Administration'
        },
        {
            'assignment_number': 'ASS-003',
            'staff_id': 'EMP-12347',
            'staff_name': 'Bob Johnson',
            'email': 'bob.johnson@hdft.nhs.uk',
            'department': 'Finance'
        }
    ]
    
    # Generate survey URLs
    generator = SurveyTokenGenerator()
    survey_urls = generator.create_survey_urls(
        staff_list=sample_staff,
        base_url='https://survey.hdft.nhs.uk'
    )
    
    print(f"✓ Generated {len(survey_urls)} personalized survey URLs\n")
    
    # Display sample
    print("Sample URL for first staff member:")
    print(f"  Name: {survey_urls[0]['staff_name']}")
    print(f"  Email: {survey_urls[0]['email']}")
    print(f"  URL: {survey_urls[0]['survey_url']}\n")
    
    # Export for bulk insert
    generator.export_for_lakehouse(survey_urls, 'output/survey_tokens.json')
    generator.export_for_csv(survey_urls, 'output/survey_urls.csv')
    
    # Generate sample email
    email = generator.generate_email_template(
        survey_urls[0]['staff_name'],
        survey_urls[0]['survey_url']
    )
    print("Sample Email:")
    print(f"Subject: {email['subject']}")
    print(f"Body:\n{email['body']}")
