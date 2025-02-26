function startAuth() {
    window.location.href = '/auth';
}

function loadCourses() {
    fetch('/courses')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('courseSelect');
            data.courses.forEach(course => {
                const option = document.createElement('option');
                option.value = course.id;
                option.textContent = course.name;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error:', error));
}

function loadAssignments() {
    const courseId = document.getElementById('courseSelect').value;
    if (!courseId) return;
    
    document.getElementById('courseId').value = courseId;
    fetch(`/assignments/${courseId}`)
        .then(response => response.json())
        .then(data => {
            const list = document.getElementById('assignmentList');
            list.innerHTML = '';
            data.assignments.forEach(assignment => {
                const li = document.createElement('li');
                li.innerHTML = `${assignment.title} (Due: ${assignment.due}, Status: ${assignment.status}) 
                    <button onclick="selectAssignment('${assignment.id}')">Select</button>`;
                list.appendChild(li);
            });
        });
}

function selectAssignment(courseId, assignmentId) {
    document.getElementById('courseId').value = courseId;
    document.getElementById('assignmentId').value = assignmentId;
}

document.getElementById('submitForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    fetch('/submit', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('message').textContent = data.message || data.error;
        loadAssignments(); // Refresh assignment list
    })
    .catch(error => console.error('Error:', error));
});

// Load courses on page load
window.onload = loadCourses;