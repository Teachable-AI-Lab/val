function confirmation(data, socket) {
    console.log("I'm here!")
    const container = document.getElementById('prompt-message');
    container.innerHTML = '';  // Clear previous content

    // Create dialog element
    const dialog = document.createElement('div');
    dialog.className = 'dialog';

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
    yesButton.onclick = () => socket.emit('response', { response: 'yes' });

    const noButton = document.createElement('button');
    noButton.className = 'no';
    noButton.textContent = 'No';
    noButton.onclick = () => socket.emit('response', { response: 'no' });

    // Append everything
    buttonsDiv.appendChild(yesButton);
    buttonsDiv.appendChild(noButton);
    dialog.appendChild(p);
    dialog.appendChild(buttonsDiv);
    container.appendChild(dialog);

    console.log(yesButton);
    console.log(noButton);
} 