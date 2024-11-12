const msgerForm = document.getElementsByClassName("msger-inputarea");
const msgerInput = document.getElementsByClassName("msger-input");
const msgerChat = document.getElementsByClassName("msger-chat");

const BOT_IMG = "../static/images/val.pic.jpg";
const PERSON_IMG = "../static/images/user.pic.jpg";
const BOT_NAME = "VAL";
const PERSON_NAME = "Me";

$(function(){
    console.log('ready');
    var socket = io();

    $('form').submit(function(e) {
        e.preventDefault();
        var input = $('input[type="text"]');
        var message = input.val().trim();
        if (message) {
            socket.emit('message', {'response': message});
            input.val('');
        }
        appendMessage(PERSON_NAME, PERSON_IMG, "right", message, null, null);
        msgerInput.value = "";

        //botResponse();
    });
    
    socket.on('message', function(data) {
        if (data['type'] == 'display_known_tasks'){
            console.log('received request_user_task', data);
            buildDialog(data, socket)
        }
        if (data['type'] == 'request_user_task'){
            console.log('received request_user_task', data);
            buildDialog(data, socket)
        }
        if (data['type'] == 'ask_subtasks'){
            console.log('received ask_subtasks', data);
            buildDialog(data, socket)
        }
        if (data['type'] == 'ask_rephrase'){
            console.log('received ask_rephrase', data);
            buildDialog(data, socket)
        }

        if (data['type'] == 'segment_confirmation'){
            console.log('received segment_confirmation', data);
            confirmation(data, socket)
        }
        if (data['type'] == 'map_confirmation'){
            console.log('received map_confirmation', data);
            confirmation(data, socket)
        }
        if (data['type'] == 'map_correction'){
            console.log('received map_correction', data);
            map_correction(data, socket)
        }
        if (data['type'] == 'map_new_method_confirmation'){
            console.log('received map_new_method_confirmation', data);
            confirmation(data, socket)
        }
        if (data['type'] == 'ground_confirmation'){
            console.log('received ground_confirmation', data);
            confirmation(data, socket)
        }
        if (data['type'] == 'ground_correction'){
            console.log('received ground_correction', data);
            ground_correction(data, socket)
        }
        if (data['type'] == 'gen_confirmation'){
            console.log('received gen_confirmation', data);
            confirmation(data, socket)
        }
        if (data['type'] == 'gen_correction'){
            console.log('received gen_correction', data);
            gen_correction(data, socket)
        }
        if (data['type'] == 'confirm_task_decomposition'){
            console.log('received confirm_task_decomposition', data);
            confirmation(data, socket)
        }
        if (data['type'] == 'confirm_task_execution'){
            console.log('received confirm_task_execution', data);
            confirmation(data, socket)
        }
    });


    function appendMessage(name, img, side, text, buttons = null, options = null) {
        const container = document.getElementById('prompt-message');
        const msgHTML = `
            <div class="msg ${side}-msg">
                <div class="msg-img" style="background-image: url(${img})"></div>
                <div class="msg-bubble">
                    <div class="msg-info">
                        <div class="msg-info-name">${name}</div>
                        <div class="msg-info-time">${formatDate(new Date())}</div>
                    </div>
                    <div class="msg-text">${text}</div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML("beforeend", msgHTML);
        container.scrollTop += 500;

        if (buttons) {
            const lastMsg = container.lastElementChild.querySelector(".msg-bubble");
            lastMsg.appendChild(buttons);
        }

        socket.emit('on log',msgHTML);

        if (options) {
            const lastMsg = container.lastElementChild.querySelector(".msg-bubble");
            lastMsg.appendChild(options);
        }
    }

    function formatDate(date) {
        const h = "0" + date.getHours();
        const m = "0" + date.getMinutes();

        return `${h.slice(-2)}:${m.slice(-2)}`;
    }

    function buildDialog(data) {
        const container = document.getElementById('prompt-message');
        //container.innerHTML ='';  // Clear previous content

        // Create dialog element
        const dialog = document.createElement('div');
        dialog.className = 'val-output';

        // Create paragraph for instructions
        const p = document.createElement('p');
        p.textContent = data['text'];

        //dialog.appendChild(p);
        //container.appendChild(dialog);
        appendMessage(BOT_NAME, BOT_IMG, "left", data['text'], null, null);
    } 
    
    function confirmation(data) {
        const container = document.getElementById('prompt-message');
        //container.innerHTML = '';  // Clear previous content

        // Create dialog element
        const dialog = document.createElement('div');
        dialog.className = 'val-output' ;

        // Create paragraph for instructions
        const p = document.createElement('p');
        p.textContent = data['text'];

        // Create buttons container
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'buttons';

        // Create Yes and No buttons
        const yesButton = document.createElement('button');
        yesButton.className = 'yes';
        yesButton.textContent = 'Yes';
        yesButton.onclick = () => {
            socket.emit('message', { response: 'yes' });
            appendMessage(PERSON_NAME, PERSON_IMG, "right", 'yes', null, null);
        };

        const noButton = document.createElement('button');
        noButton.className = 'no';
        noButton.textContent = 'No';
        noButton.onclick = () => {
            socket.emit('message', { response: 'no' });
            appendMessage(PERSON_NAME, PERSON_IMG, "right", 'no', null, null);
        };

        // Append everything
        buttonsDiv.appendChild(yesButton);
        buttonsDiv.appendChild(noButton);
        //dialog.appendChild(p);
        //dialog.appendChild(buttonsDiv);
        //container.appendChild(dialog);
        appendMessage(BOT_NAME, BOT_IMG, "left", data['text'], buttonsDiv);
    } 

    function ground_confirmation(data) {
        const container = document.getElementById('prompt-message');
        //container.innerHTML = '';  // Clear previous content

        // Create dialog element
        const dialog = document.createElement('div');
        dialog.className = 'val-output' ;

        //const taskName = data['task_name'] || '未提供任务名称';
        const taskArgsText = data['task_args'] || '未提供参数';

        const fullText = `(${taskArgsText})`;

        const p = document.createElement('p');
        p.textContent = fullText;

        // Create paragraph for instructions
        //const p = document.createElement('p');
        //p.textContent = data['text'];

        // Create buttons container
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'buttons';

        // Create Yes and No buttons
        const yesButton = document.createElement('button');
        yesButton.className = 'yes';
        yesButton.textContent = 'Yes';
        yesButton.onclick = () => {
            socket.emit('message', { response: 'yes' });
            appendMessage(PERSON_NAME, PERSON_IMG, "right", 'yes', null, null);
        };

        const noButton = document.createElement('button');
        noButton.className = 'no';
        noButton.textContent = 'No';
        noButton.onclick = () => {
            socket.emit('message', { response: 'no' });
            appendMessage(PERSON_NAME, PERSON_IMG, "right", 'no', null, null);
        };

        // Append everything
        buttonsDiv.appendChild(yesButton);
        buttonsDiv.appendChild(noButton);
        dialog.appendChild(p);
        //dialog.appendChild(buttonsDiv);
        //container.appendChild(dialog);
        appendMessage(BOT_NAME, BOT_IMG, "left", data['text'], dialog, buttonsDiv);
    } 

    function gen_confirmation(data) {
        const container = document.getElementById('prompt-message');
        //container.innerHTML = '';  // Clear previous content

        // Create dialog element
        const dialog = document.createElement('div');
        dialog.className = 'val-output' ;

        // Create paragraph for instructions
        const p = document.createElement('p');
        p.textContent = data['text'];

        // Create buttons container
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'buttons';

        // Create Yes and No buttons
        const yesButton = document.createElement('button');
        yesButton.className = 'yes';
        yesButton.textContent = 'Yes';
        yesButton.onclick = () => {
            socket.emit('message', { response: 'yes' });
            appendMessage(PERSON_NAME, PERSON_IMG, "right", 'yes', null, null);
        };

        const noButton = document.createElement('button');
        noButton.className = 'no';
        noButton.textContent = 'No';
        noButton.onclick = () => {
            socket.emit('message', { response: 'no' });
            appendMessage(PERSON_NAME, PERSON_IMG, "right", 'no', null, null);
        };

        // Append everything
        buttonsDiv.appendChild(yesButton);
        buttonsDiv.appendChild(noButton);
        //dialog.appendChild(p);
        //dialog.appendChild(buttonsDiv);
        //container.appendChild(dialog);
        appendMessage(BOT_NAME, BOT_IMG, "left", data['text'], buttonsDiv);
    } 

    function map_correction(data) {
    
        const container = document.getElementById('prompt-message');
        //container.innerHTML = '';  // Clear previous content

        var known_tasks = data['known_tasks'];

        // Create dialog element
        const dialog = document.createElement('div');
        dialog.className = 'val-output';

        // Create paragraph for instructions
        const p = document.createElement('p');
        p.textContent = data['text'];
        //dialog.appendChild(p);

        // Create form for radio buttons
        const form = document.createElement('form');
        form.className = 'options-form';

        //Create dropdown menu
        const select = document.createElement('select');
        select.name = 'task-options';

        known_tasks.forEach((task, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = task;
            select.appendChild(option);
        });

        form.appendChild(select);

        const submitButton = document.createElement('button');
        submitButton.type = 'button'; 
        submitButton.textContent = 'Submit';
        submitButton.onclick = () => {
            const selectedOption = select.value;
            socket.emit('message', {response: selectedOption});
        };

        form.appendChild(submitButton);
        //dialog.appendChild(p);
        dialog.appendChild(form);
        //dialog.appendChild(form);
        //container.appendChild(dialog);
        appendMessage(BOT_NAME, BOT_IMG, "left", data['text'], null, dialog);
    }

    function ground_correction(data) {
        const container = document.getElementById('prompt-message');
        //container.innerHTML = '';  // Clear previous content

        var envObjects = data['env_Objects'];

        // Create dialog element
        const dialog = document.createElement('div');
        dialog.className = 'val-output';

        // Create paragraph for instructions
        const p = document.createElement('p');
        p.textContent = data.msg;
        //dialog.appendChild(p);

        // Create form for the dropdown
        const form = document.createElement('form');
        form.className = 'options-form';
        const select = document.createElement('select');
        select.id = 'obj-option';

        envObjects.forEach((obj, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = obj;
            select.appendChild(option);
        });

        form.appendChild(select);

        const submitButton = document.createElement('button');
        submitButton.type = 'button'; // Prevent form submission
        submitButton.textContent = 'Submit';
        submitButton.onclick = () => {
            const selectedOption = document.getElementById('obj-option').value;
            socket.emit('ground_correction_response', { response: selectedOption });
        };

        form.appendChild(submitButton);
        //dialog.appendChild(form);
        //container.appendChild(dialog);
        appendMessage(BOT_NAME, BOT_IMG, "left", data['text'], null, form);
    }

    function gen_correction(data) {
        const container = document.getElementById('prompt-message');
        //container.innerHTML = '';  // Clear previous content

        var envObjects = data['env_Objects']; 

        const form = document.createElement('form');
        form.onsubmit = function(e) {
            e.preventDefault();
            const checkboxes = Array.from(document.querySelectorAll('.object-checkbox:checked'));
            const indices = checkboxes.map(checkbox => envObjects.indexOf(checkbox.value));
            socket.emit('gen_correction_response', { indices: indices });
        };

        const label = document.createElement('label');
        label.textContent = 'Select the correct objects:';
        label.htmlFor = 'object-select';

        envObjects.forEach((obj, index) => {
            const checkboxLabel = document.createElement('label');
            checkboxLabel.className = 'checkbox-container';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'object-checkbox';
            checkbox.value = obj;

            const span = document.createElement('span');
            span.textContent = obj;
            span.className = 'checkmark';

            checkboxLabel.appendChild(checkbox);
            checkboxLabel.appendChild(span);
            form.appendChild(checkboxLabel);
        });

        const submitButton = document.createElement('button');
        submitButton.type = 'submit';
        submitButton.textContent = 'Submit';

        form.appendChild(submitButton);
        container.appendChild(form);
        appendMessage(BOT_NAME, BOT_IMG, "left", data['text'], null, form);
    }
});