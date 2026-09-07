/**
 * HDFT Staff Survey - Main Application
 * Handles token validation, survey loading, and response submission
 */

class SurveyApp {
    constructor() {
        this.token = null;
        this.tokenData = null;
        this.questions = [];
        this.responses = {};
        this.currentQuestionIndex = 0;
        this.startTime = null;

        this.setupEventListeners();
        this.initializeApp();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Landing page button
        const continueBtn = document.getElementById('continue-intro');
        if (continueBtn) {
            continueBtn.addEventListener('click', () => this.closeLandingPage());
        }

        // Survey form
        const surveyForm = document.getElementById('survey-form');
        if (surveyForm) {
            surveyForm.addEventListener('submit', (e) => this.handleSurveySubmit(e));
        }

        // Navigation buttons
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        if (prevBtn) prevBtn.addEventListener('click', () => this.previousQuestion());
        if (nextBtn) nextBtn.addEventListener('click', () => this.nextQuestion());
    }

    /**
     * Initialize the application
     */
    async initializeApp() {
        // Check for token in URL - staff receive individualized URLs via email
        const urlParams = new URLSearchParams(window.location.search);
        const tokenParam = urlParams.get('token');

        if (tokenParam) {
            this.token = tokenParam;
            console.log('Token found in URL:', this.token);
            // Wait for landing page animation to complete (8.6s) before validating
            setTimeout(() => this.validateToken(), 9000);
        }
    }

    /**
     * Close landing page and proceed to survey
     */
    closeLandingPage() {
        const landing = document.getElementById('landing');
        if (landing) {
            console.log('Closing landing page');
            landing.classList.add('leaving');
            setTimeout(() => {
                landing.classList.add('hidden');
                // Load survey after landing page is hidden
                this.loadSurvey();
            }, 650);
        }
    }

    /**
     * Handle token form submission
     */
    async handleTokenSubmit(e) {
        e.preventDefault();
        
        const tokenInput = document.getElementById('token-input');
        this.token = tokenInput.value.trim();

        if (!this.token) {
            this.showTokenError('Please enter your survey token');
            return;
        }

        await this.validateToken();
    }

    /**
     * Validate token via API
     */
    async validateToken() {
        try {
            console.log('Validating token:', this.token);
            this.showLoading();

            const response = await fetch(
                `/api/validate-token?token=${encodeURIComponent(this.token)}`
            );

            console.log('Token validation response:', response.status);

            if (!response.ok) {
                throw new Error(`Token validation failed: ${response.status}`);
            }

            const data = await response.json();
            console.log('Token data received:', data);
            
            if (!data.valid) {
                this.showError(
                    'Invalid Token',
                    data.error || 'The survey token is no longer valid. Please contact HR.'
                );
                this.hideLoading();
                return;
            }

            this.tokenData = data.data;
            console.log('Token valid, staff:', this.tokenData.staff_name);

            // Check if already submitted
            if (this.tokenData.already_submitted) {
                this.showAlreadySubmitted();
                this.hideLoading();
                return;
            }

            // Close landing page with animation then load survey
            this.hideLoading();
            this.closeLandingPage();
        } catch (error) {
            console.error('Token validation error:', error);
            this.showError(
                'Error',
                'An error occurred while validating your token. Please try again or contact HR.'
            );
            this.hideLoading();
        }
    }

    /**
     * Load survey questions
     */
    async loadSurvey() {
        try {
            console.log('Loading survey questions from API');
            const response = await fetch('/api/survey');

            console.log('Survey API response:', response.status);

            if (!response.ok) {
                throw new Error(`Failed to load survey: ${response.status}`);
            }

            const data = await response.json();
            console.log('Survey data received:', data);
            
            this.questions = data.questions || [];

            if (this.questions.length === 0) {
                throw new Error('No questions found');
            }

            console.log(`Loaded ${this.questions.length} questions`);

            // Initialize responses object
            this.questions.forEach(q => {
                this.responses[q.question_id] = null;
            });

            // Show survey page
            this.showSurveyPage();
            this.renderCurrentQuestion();
            this.startTime = Date.now();

        } catch (error) {
            console.error('Error loading survey:', error);
            this.showError('Error', 'Failed to load survey. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Determine if a question should be displayed based on branching logic
     */
    shouldShowQuestion(question) {
        // Parent questions or always_show questions are always displayed
        if (!question.parent_question_id || question.branch_type === 'always_show') {
            return true;
        }

        // For conditional questions, check if parent was answered with "Yes"
        if (question.branch_type === 'conditional') {
            const parentQuestion = this.questions.find(q => q.question_id === question.parent_question_id);
            if (!parentQuestion) return false;

            const parentResponse = this.responses[question.parent_question_id];
            
            // Check if parent answer equals show_if_answer value
            if (question.show_if_answer === 'Yes') {
                return parentResponse === 'Yes';
            }
            return false;
        }

        return false;
    }

    /**
     * Get only the questions that should be displayed
     */
    getVisibleQuestions() {
        const visible = this.questions.filter(q => this.shouldShowQuestion(q));
        console.log('getVisibleQuestions:', {
            total: this.questions.length,
            visible: visible.length,
            questions: visible.map(q => ({id: q.question_id, branch: q.branch_type}))
        });
        return visible;
    }

    /**
     * Get current visible question index
     */
    getCurrentVisibleQuestion() {
        const visibleQuestions = this.getVisibleQuestions();
        if (this.currentQuestionIndex < 0 || this.currentQuestionIndex >= visibleQuestions.length) {
            return null;
        }
        return visibleQuestions[this.currentQuestionIndex];
    }

    /**
     * Render current question
     */
    renderCurrentQuestion() {
        const visibleQuestions = this.getVisibleQuestions();
        console.log('renderCurrentQuestion called:', {
            visibleQuestionsCount: visibleQuestions.length,
            currentIndex: this.currentQuestionIndex,
            totalQuestions: this.questions.length
        });
        
        if (this.currentQuestionIndex < 0 || this.currentQuestionIndex >= visibleQuestions.length) {
            console.log('Invalid question index, returning');
            return;
        }

        const container = document.getElementById('questions-container');
        console.log('Container element:', container);
        
        if (!container) {
            console.error('questions-container not found!');
            return;
        }

        container.innerHTML = '';

        const question = visibleQuestions[this.currentQuestionIndex];
        console.log('Rendering question:', question.question_id, question.question_text);
        
        const questionElement = this.createQuestionElement(question, this.currentQuestionIndex, visibleQuestions.length);
        container.appendChild(questionElement);
        console.log('Question element appended to container');

        this.updateProgressBar();
        this.updateNavigationButtons();

        // Restore previous answer if exists
        if (this.responses[question.question_id] !== null) {
            this.restoreAnswer(question);
        }
    }

    /**
     * Create question element
     */
    createQuestionElement(question, currentIndex, totalVisible) {
        const group = document.createElement('div');
        group.className = 'question-group';

        const questionNum = currentIndex + 1;
        const questionLabel = document.createElement('label');
        questionLabel.className = 'question-label';
        questionLabel.innerHTML = `
            <div class="question-number">Question ${questionNum} of ${totalVisible}</div>
            <div>${this.escapeHtml(question.question_text)}</div>
        `;
        group.appendChild(questionLabel);

        // Create answer options based on type
        const answerContainer = document.createElement('div');
        answerContainer.className = 'answer-container';

        switch (question.answer_type.toLowerCase()) {
            case 'likert':
                this.createLikertOptions(answerContainer, question);
                break;
            case 'multiple_choice':
                this.createCheckboxOptions(answerContainer, question);
                break;
            case 'text':
                this.createTextInput(answerContainer, question);
                break;
            case 'textarea':
                this.createTextArea(answerContainer, question);
                break;
            default:
                this.createTextInput(answerContainer, question);
        }

        group.appendChild(answerContainer);
        return group;
    }

    /**
     * Create Likert scale options
     */
    createLikertOptions(container, question) {
        let options = question.answer_options;
        
        // Parse JSON array if it's a string
        if (typeof options === 'string') {
            try {
                options = JSON.parse(options);
            } catch (e) {
                options = [];
            }
        }

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'likert-options';

        options.forEach((option) => {
            const label = document.createElement('label');
            
            const input = document.createElement('input');
            input.type = 'radio';
            input.name = `question_${question.question_id}`;
            input.value = option;
            input.required = question.is_required;
            input.addEventListener('change', () => {
                this.responses[question.question_id] = option;
                // Re-render to show/hide conditional questions
                this.renderCurrentQuestion();
            });

            const optionLabel = document.createElement('div');
            optionLabel.className = 'likert-option';
            optionLabel.textContent = option;

            label.appendChild(input);
            label.appendChild(optionLabel);
            optionsDiv.appendChild(label);
        });

        container.appendChild(optionsDiv);
    }

    /**
     * Create checkbox options (multiple choice)
     */
    createCheckboxOptions(container, question) {
        let options = question.answer_options;
        
        // Parse JSON array if it's a string
        if (typeof options === 'string') {
            try {
                options = JSON.parse(options);
            } catch (e) {
                options = [];
            }
        }

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'checkbox-options';

        options.forEach((option) => {
            const label = document.createElement('label');
            label.className = 'checkbox-option';

            const input = document.createElement('input');
            input.type = 'checkbox';
            input.name = `question_${question.question_id}`;
            input.value = option;
            input.addEventListener('change', () => {
                this.updateMultipleChoiceResponse(question.question_id);
                // Re-render to show/hide conditional questions
                this.renderCurrentQuestion();
            });

            label.appendChild(input);
            label.appendChild(document.createTextNode(this.escapeHtml(option)));
            optionsDiv.appendChild(label);
        });

        container.appendChild(optionsDiv);
    }

    /**
     * Create text input
     */
    createTextInput(container, question) {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control text-input';
        input.placeholder = 'Enter your response';
        input.required = question.is_required;
        input.addEventListener('change', () => {
            this.responses[question.question_id] = input.value;
        });

        container.appendChild(input);
    }

    /**
     * Create text area
     */
    createTextArea(container, question) {
        const textarea = document.createElement('textarea');
        textarea.className = 'form-control text-area';
        textarea.placeholder = 'Enter your response';
        textarea.required = question.is_required;
        textarea.addEventListener('change', () => {
            this.responses[question.question_id] = textarea.value;
        });

        container.appendChild(textarea);
    }

    /**
     * Update multiple choice response
     */
    updateMultipleChoiceResponse(questionId) {
        const checkboxes = document.querySelectorAll(
            `input[name="question_${questionId}"]:checked`
        );
        const values = Array.from(checkboxes).map(cb => cb.value);
        this.responses[questionId] = values.length > 0 ? values : null;
    }

    /**
     * Restore previous answer
     */
    restoreAnswer(question) {
        const savedValue = this.responses[question.question_id];
        
        if (!savedValue) return;

        if (question.answer_type.toLowerCase() === 'likert') {
            const radio = document.querySelector(
                `input[name="question_${question.question_id}"][value="${savedValue}"]`
            );
            if (radio) radio.checked = true;
        } else if (question.answer_type.toLowerCase() === 'multiple_choice') {
            const values = Array.isArray(savedValue) ? savedValue : [savedValue];
            values.forEach(value => {
                const checkbox = document.querySelector(
                    `input[name="question_${question.question_id}"][value="${value}"]`
                );
                if (checkbox) checkbox.checked = true;
            });
        } else if (question.answer_type.toLowerCase() === 'text') {
            const input = document.querySelector('.text-input');
            if (input) input.value = savedValue;
        } else if (question.answer_type.toLowerCase() === 'textarea') {
            const textarea = document.querySelector('.text-area');
            if (textarea) textarea.value = savedValue;
        }
    }

    /**
     * Navigate to next question
     */
    nextQuestion() {
        const visibleQuestions = this.getVisibleQuestions();
        if (this.currentQuestionIndex < visibleQuestions.length - 1) {
            this.currentQuestionIndex++;
            this.renderCurrentQuestion();
        }
    }

    /**
     * Navigate to previous question
     */
    previousQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.renderCurrentQuestion();
        }
    }

    /**
     * Update progress bar
     */
    updateProgressBar() {
        const visibleQuestions = this.getVisibleQuestions();
        const progress = visibleQuestions.length > 0 ? 
            ((this.currentQuestionIndex + 1) / visibleQuestions.length) * 100 : 0;
        const progressFill = document.getElementById('progress-fill');
        const currentQuestion = document.getElementById('current-question');
        const totalQuestions = document.getElementById('total-questions');

        if (progressFill) progressFill.style.width = progress + '%';
        if (currentQuestion) currentQuestion.textContent = this.currentQuestionIndex + 1;
        if (totalQuestions) totalQuestions.textContent = visibleQuestions.length;
    }

    /**
     * Update navigation buttons
     */
    updateNavigationButtons() {
        const visibleQuestions = this.getVisibleQuestions();
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const submitBtn = document.getElementById('submit-btn');

        if (prevBtn) {
            prevBtn.classList.toggle('hidden', this.currentQuestionIndex === 0);
        }

        const isLastQuestion = this.currentQuestionIndex === visibleQuestions.length - 1;

        if (nextBtn) {
            nextBtn.classList.toggle('hidden', isLastQuestion);
        }

        if (submitBtn) {
            submitBtn.classList.toggle('hidden', !isLastQuestion);
        }
    }

    /**
     * Handle survey submission
     */
    async handleSurveySubmit(e) {
        e.preventDefault();

        // Validate all responses
        if (!this.validateResponses()) {
            this.showSurveyError('Please answer all required questions');
            return;
        }

        try {
            this.showLoading();

            const payload = {
                token: this.token,
                responses: this.responses
            };

            const response = await fetch('/api/submit-response', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to submit survey');
            }

            const data = await response.json();

            // Show thank you page
            this.showThankYouPage();

        } catch (error) {
            console.error('Error submitting survey:', error);
            this.showSurveyError('Error submitting survey. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Validate all responses
     */
    validateResponses() {
        // Only validate visible questions
        const visibleQuestions = this.getVisibleQuestions();
        for (const question of visibleQuestions) {
            if (question.is_required && !this.responses[question.question_id]) {
                return false;
            }
        }
        return true;
    }

    /**
     * Show error for token
     */
    showTokenError(message) {
        const errorDiv = document.getElementById('token-error');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }
    }

    /**
     * Show error for survey
     */
    showSurveyError(message) {
        const errorDiv = document.getElementById('survey-error');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }
    }

    /**
     * Show error page
     */
    showError(title, message) {
        // Make sure app container is visible
        const appContainer = document.getElementById('app');
        if (appContainer) {
            appContainer.style.display = 'block';
        }

        document.getElementById('token-entry').classList.add('hidden');
        document.getElementById('survey-page').classList.add('hidden');
        document.getElementById('thank-you-page').classList.add('hidden');
        document.getElementById('error-page').classList.remove('hidden');

        document.getElementById('error-title').textContent = title;
        document.getElementById('error-message').textContent = message;
    }

    /**
     * Show already submitted message
     */
    showAlreadySubmitted() {
        this.showError(
            'Already Submitted',
            'This survey token has already been used. Thank you for your participation!'
        );
    }

    /**
     * Show survey page
     */
    showSurveyPage() {
        console.log('showSurveyPage called');
        
        // Make sure app container is visible
        const appContainer = document.getElementById('app');
        if (appContainer) {
            console.log('Setting app container display to block');
            appContainer.style.display = 'block';
        } else {
            console.error('app container not found!');
        }

        const tokenEntry = document.getElementById('token-entry');
        const surveyPage = document.getElementById('survey-page');
        const thankYouPage = document.getElementById('thank-you-page');
        const errorPage = document.getElementById('error-page');
        
        console.log('Element status:', {
            tokenEntry: !!tokenEntry,
            surveyPage: !!surveyPage,
            thankYouPage: !!thankYouPage,
            errorPage: !!errorPage
        });

        if (tokenEntry) tokenEntry.classList.add('hidden');
        if (surveyPage) surveyPage.classList.remove('hidden');
        if (thankYouPage) thankYouPage.classList.add('hidden');
        if (errorPage) errorPage.classList.add('hidden');

        // Clear any error messages
        const errorDiv = document.getElementById('survey-error');
        if (errorDiv) errorDiv.classList.add('hidden');
        
        console.log('Survey page shown');
    }

    /**
     * Show thank you page
     */
    showThankYouPage() {
        document.getElementById('token-entry').classList.add('hidden');
        document.getElementById('survey-page').classList.add('hidden');
        document.getElementById('thank-you-page').classList.remove('hidden');
        document.getElementById('error-page').classList.add('hidden');
    }

    /**
     * Show loading spinner
     */
    showLoading() {
        const loading = document.getElementById('loading');
        if (loading) loading.classList.remove('hidden');
    }

    /**
     * Hide loading spinner
     */
    hideLoading() {
        const loading = document.getElementById('loading');
        if (loading) loading.classList.add('hidden');
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.surveyApp = new SurveyApp();
});
