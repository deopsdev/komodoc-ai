document.addEventListener('DOMContentLoaded', () => {
    const sendButton = document.getElementById('send-button');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');

    // Function to add a message to the chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        messageDiv.textContent = text;
        chatMessages.appendChild(messageDiv);
        
        // Scroll to the bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Function to handle sending the message
    async function sendMessage() {
        const text = userInput.value.trim();
        if (text === '') return;

        // Add user message
        addMessage(text, 'user');
        userInput.value = '';

        // Add loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.classList.add('message', 'system');
        loadingDiv.textContent = 'Komodoc thinking...';
        chatMessages.appendChild(loadingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            // Call local backend
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: text })
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            // Remove loading indicator
            chatMessages.removeChild(loadingDiv);

            // Add AI response
            if (data.error) {
                addMessage('Error: ' + data.error, 'system');
            } else {
                addMessage(data.reply, 'ai');
            }

        } catch (error) {
            console.error('Error:', error);
            chatMessages.removeChild(loadingDiv);
            addMessage('Sorry, I encountered an error. Please ensure the server is running.', 'system');
        }
    }

    // Event listeners
    sendButton.addEventListener('click', sendMessage);

    // Save chat functionality
    const saveButton = document.getElementById('save-button');
    saveButton.addEventListener('click', () => {
        const messages = Array.from(chatMessages.querySelectorAll('.message'));
        let chatHistory = '';

        messages.forEach(msg => {
            const role = msg.classList.contains('user') ? 'You' : 
                         msg.classList.contains('ai') ? 'Komodoc' : 'System';
            chatHistory += `${role}: ${msg.textContent}\n\n`;
        });

        const blob = new Blob([chatHistory], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const now = new Date();
        const timestamp = now.getFullYear() + '-' + 
                          String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                          String(now.getDate()).padStart(2, '0') + '_' + 
                          String(now.getHours()).padStart(2, '0') + '-' + 
                          String(now.getMinutes()).padStart(2, '0') + '-' + 
                          String(now.getSeconds()).padStart(2, '0');
        a.download = `chat-history-${timestamp}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
