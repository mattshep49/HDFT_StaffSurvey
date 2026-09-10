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
            continueBtn.addEventListener('click', () => {
                if (this.token) {
                    this.validateToken();
                } else {
                    this.closeLandingPage();
                }
            });
        }

        // Skip button mirrors continue-intro but skips the animation delay
        const skipBtn = document.getElementById('skip');
        if (skipBtn) {
            skipBtn.addEventListener('click', () => {
                if (this.token) {
                    this.validateToken();
                } else {
                    this.closeLandingPage();
                }
            });
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
            // Don't auto-validate - let landing page animate and user clicks "Begin the survey"
            // The continue-intro button click will trigger validation
        }
    }

    /**
     * Close landing page and proceed to survey
     */
    closeLandingPage() {
        const landing = document.getElementById('landing');
        if (landing) {
            console.log('Closing landing page');
            
            // Ensure .logo class is added (shows DOT logo/identity section)
            if (!landing.classList.contains('logo')) {
                console.log('Adding .logo class to show identity/DOT logo');
                landing.classList.add('logo');
            }
            
            console.log('Landing element before changes:', {
                display: window.getComputedStyle(landing).display,
                visibility: window.getComputedStyle(landing).visibility,
                zIndex: window.getComputedStyle(landing).zIndex
            });
            
            landing.classList.add('leaving');
            setTimeout(() => {
                landing.classList.add('hidden');
                console.log('Landing element after hidden class:', {
                    display: window.getComputedStyle(landing).display,
                    visibility: window.getComputedStyle(landing).visibility,
                    zIndex: window.getComputedStyle(landing).zIndex
                });
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

            if (response.status === 401) {
                this.showInvalidToken();
                this.hideLoading();
                return;
            }

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

        // For conditional questions, check if parent was answered with the expected value
        if (question.branch_type === 'conditional') {
            const parentResponse = this.responses[question.parent_question_id];
            if (parentResponse === null || parentResponse === undefined) {
                console.log(`Branching: ${question.question_id} hidden - parent ${question.parent_question_id} not answered yet`);
                return false;
            }

            let condition = question.show_if_answer;
            let isNegation = false;

            // Handle negation syntax: "not X" means show if NOT X
            if (typeof condition === 'string' && condition.toLowerCase().startsWith('not ')) {
                isNegation = true;
                condition = condition.substring(4).trim(); // Remove "not " prefix
            }

            let result = false;

            // multiple_choice stores an array; likert/text stores a string
            if (Array.isArray(parentResponse)) {
                if (isNegation) {
                    result = !parentResponse.includes(condition);
                    console.log(`Branching: ${question.question_id} - parent response [${parentResponse.join(', ')}], checking NOT "${condition}" = ${result}`);
                } else {
                    result = parentResponse.includes(condition);
                    console.log(`Branching: ${question.question_id} - parent response [${parentResponse.join(', ')}], checking for "${condition}" = ${result}`);
                }
            } else {
                if (isNegation) {
                    result = parentResponse !== condition;
                    console.log(`Branching: ${question.question_id} - parent response "${parentResponse}", checking NOT "${condition}" = ${result}`);
                } else {
                    result = parentResponse === condition;
                    console.log(`Branching: ${question.question_id} - parent response "${parentResponse}", checking for "${condition}" = ${result}`);
                }
            }

            return result;
        }

        return false;
    }

    /**
     * Get only the questions that should be displayed (parent questions only for navigation)
     */
    getVisibleQuestions() {
        // Return only parent questions for main navigation
        const visible = this.questions.filter(q => {
            return !q.parent_question_id || q.branch_type === 'always_show';
        }).filter(q => this.shouldShowQuestion(q));
        
        console.log('getVisibleQuestions (parents only):', {
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
     * Recursively get all visible descendants (children, grandchildren, etc.)
     */
    getAllVisibleDescendants(parentQuestionId) {
        const directChildren = this.questions
            .filter(q => q.parent_question_id === parentQuestionId && this.shouldShowQuestion(q))
            .sort((a, b) => a.sequence - b.sequence);
        const all = [];
        directChildren.forEach(child => {
            all.push(child);
            all.push(...this.getAllVisibleDescendants(child.question_id));
        });
        return all;
    }

    /**
     * Render current question with inline conditional children
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
        
        if (!container) {
            console.error('questions-container not found!');
            return;
        }

        container.innerHTML = '';

        const question = visibleQuestions[this.currentQuestionIndex];
        console.log('Rendering question:', question.question_id, question.question_text);
        
        const questionWrapper = document.createElement('div');
        questionWrapper.className = 'question-wrapper';
        
        // Render parent question
        const questionElement = this.createQuestionElement(question, this.currentQuestionIndex, visibleQuestions.length);
        questionWrapper.appendChild(questionElement);
        
        // Render all visible conditional descendants inline (children, grandchildren, etc.)
        const visibleChildren = this.getAllVisibleDescendants(question.question_id);
        console.log(`Question ${question.question_id} has ${visibleChildren.length} visible descendants`);
        
        visibleChildren.forEach((childQuestion, childIndex) => {
            const childElement = this.createQuestionElement(childQuestion, -1, -1); // -1 means inline child
            childElement.classList.add('conditional-child');
            childElement.style.marginLeft = '2rem';
            childElement.style.marginTop = '1.5rem';
            childElement.style.paddingLeft = '1.5rem';
            childElement.style.borderLeft = '3px solid #41c7ed';
            questionWrapper.appendChild(childElement);
        });
        
        // Append to DOM FIRST so querySelector can find the inputs
        container.appendChild(questionWrapper);
        console.log('Question and children appended to container');

        this.updateProgressBar();
        this.updateNavigationButtons();

        // Restore answers after DOM is live
        if (this.responses[question.question_id] !== null) {
            this.restoreAnswer(question);
        }

        visibleChildren.forEach((childQuestion) => {
            if (this.responses[childQuestion.question_id] !== null) {
                this.restoreAnswer(childQuestion);
            }
        });
    }

    /**
     * Create question element
     */
    createQuestionElement(question, currentIndex, totalVisible) {
        const group = document.createElement('div');
        group.className = 'question-group';

        // Only show question number if this is a main question (currentIndex >= 0)
        if (currentIndex >= 0) {
            const questionNum = currentIndex + 1;
            // Q2: append Q1's selected emotion(s) into the question text
            let displayText = question.question_text;
            if (question.question_id === 'Q2') {
                const q1Response = this.responses['Q1'];
                if (q1Response && q1Response.length > 0) {
                    const emotions = Array.isArray(q1Response) ? q1Response.join(', ') : q1Response;
                    displayText = question.question_text.replace('...', ' ' + emotions);
                }
            }
            const questionLabel = document.createElement('label');
            questionLabel.className = 'question-label';
            questionLabel.innerHTML = `
                <div class="question-number">Question ${questionNum} of ${totalVisible}</div>
                <div>${this.escapeHtml(displayText)}</div>
            `;
            group.appendChild(questionLabel);
            // Q1 multi-select hint
            if (question.question_id === 'Q1') {
                const hint = document.createElement('p');
                hint.className = 'answer-hint';
                hint.textContent = 'Please select the best 3 options';
                group.appendChild(hint);
            }
        } else {
            // Inline child question (no number) - use div instead of label to avoid label nesting with form inputs
            const questionDiv = document.createElement('div');
            questionDiv.className = 'question-label conditional-child-label';
            questionDiv.style.fontWeight = '600';
            questionDiv.style.color = '#41c7ed';
            questionDiv.style.marginBottom = '0.5rem';
            
            const arrow = document.createElement('span');
            arrow.textContent = '↳ ';
            questionDiv.appendChild(arrow);
            
            const text = document.createTextNode(this.escapeHtml(question.question_text));
            questionDiv.appendChild(text);
            
            group.appendChild(questionDiv);
        }

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
     * Create checkbox/radio options (multiple choice)
     * Q1 uses multi-select checkboxes; all other questions use single-select radio buttons
     */
    createCheckboxOptions(container, question) {
        let options = question.answer_options;
        
        if (typeof options === 'string') {
            try {
                options = JSON.parse(options);
            } catch (e) {
                options = [];
            }
        }

        const isMultiSelect = question.question_id === 'Q1' || question.question_id === 'Q16';
        const inputType = isMultiSelect ? 'checkbox' : 'radio';

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'checkbox-options';

        options.forEach((option) => {
            const label = document.createElement('label');
            label.className = 'checkbox-option';

            const input = document.createElement('input');
            input.type = inputType;
            input.name = `question_${question.question_id}`;
            input.value = option;
            
            input.addEventListener('change', () => {
                if (isMultiSelect) {
                    this.updateMultipleChoiceResponse(question.question_id);
                } else {
                    this.responses[question.question_id] = option;
                }
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
        
        console.log(`Restoring answer for ${question.question_id}:`, {
            savedValue: savedValue,
            answerType: question.answer_type,
            allInputsWithName: document.querySelectorAll(`input[name="question_${question.question_id}"]`).length
        });
        
        if (!savedValue) return;

        if (question.answer_type.toLowerCase() === 'likert') {
            const radio = document.querySelector(
                `input[name="question_${question.question_id}"][value="${savedValue}"]`
            );
            if (radio) {
                radio.checked = true;
                console.log(`Restored radio for ${question.question_id}: ${savedValue}`);
            }
        } else if (question.answer_type.toLowerCase() === 'multiple_choice') {
            const values = Array.isArray(savedValue) ? savedValue : [savedValue];
            console.log(`Restoring checkboxes for ${question.question_id}:`, values);
            values.forEach(value => {
                const checkbox = document.querySelector(
                    `input[name="question_${question.question_id}"][value="${value}"]`
                );
                if (checkbox) {
                    checkbox.checked = true;
                    console.log(`  ✓ Checked: ${value}`);
                } else {
                    console.log(`  ✗ Not found: ${value}`);
                }
            });
        } else if (question.answer_type.toLowerCase() === 'text') {
            const input = document.querySelector(`input[name="question_${question.question_id}"].text-input`);
            if (input) input.value = savedValue;
        } else if (question.answer_type.toLowerCase() === 'textarea') {
            const textarea = document.querySelector(`textarea[name="question_${question.question_id}"].text-area`);
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

        // Validate all responses — navigates to first unanswered question if incomplete
        if (!this.validateResponses()) {
            this.showSurveyError('Please answer this question before submitting.');
            return;
        }

        try {
            this.showLoading();

            // Sort responses by question sequence order
            const sortedResponses = {};
            this.questions
                .filter(q => this.responses[q.question_id] !== null && this.responses[q.question_id] !== undefined)
                .sort((a, b) => a.sequence - b.sequence)
                .forEach(q => { sortedResponses[q.question_id] = this.responses[q.question_id]; });

            const payload = {
                token: this.token,
                responses: sortedResponses
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
     * Validate all responses; navigates to first unanswered question if any are missing
     */
    validateResponses() {
        const visibleQuestions = this.getVisibleQuestions();
        for (let i = 0; i < visibleQuestions.length; i++) {
            const question = visibleQuestions[i];
            const response = this.responses[question.question_id];
            const isEmpty = response === null || response === undefined ||
                            (Array.isArray(response) && response.length === 0) ||
                            response === '';
            if (question.is_required && isEmpty) {
                this.currentQuestionIndex = i;
                this.renderCurrentQuestion();
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
    showInvalidToken() {
        const landing = document.getElementById('landing');
        if (landing) landing.classList.add('hidden');
        this.showError(
            'Unrecognised Survey Link',
            'Sorry, this survey link was not recognised or has already been submitted. If you believe this is an error, please contact the People Team.'
        );
    }

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
            console.log('App container computed style:', {
                display: window.getComputedStyle(appContainer).display,
                visibility: window.getComputedStyle(appContainer).visibility,
                height: window.getComputedStyle(appContainer).height,
                zIndex: window.getComputedStyle(appContainer).zIndex
            });
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

        if (tokenEntry) {
            tokenEntry.classList.add('hidden');
            console.log('Token entry hidden');
        }
        
        if (surveyPage) {
            // Make absolutely sure hidden class is removed
            surveyPage.classList.remove('hidden');
            surveyPage.style.display = 'flex';
            surveyPage.style.visibility = 'visible';
            surveyPage.style.opacity = '1';
            console.log('Survey page unhidden with inline styles');
            console.log('Survey page computed style after unhiding:', {
                display: window.getComputedStyle(surveyPage).display,
                visibility: window.getComputedStyle(surveyPage).visibility,
                height: window.getComputedStyle(surveyPage).height,
                zIndex: window.getComputedStyle(surveyPage).zIndex,
                opacity: window.getComputedStyle(surveyPage).opacity
            });
        }
        
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
        const thankYouPage = document.getElementById('thank-you-page');
        thankYouPage.classList.remove('hidden');
        document.getElementById('error-page').classList.add('hidden');
        setTimeout(() => thankYouPage.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
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
