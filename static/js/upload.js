document.addEventListener('DOMContentLoaded', () => {
    const elements = {
        fileInput: document.getElementById('file'),
        dropzone: document.getElementById('dropzone'),
        fileList: document.getElementById('file-list'),
        uploadForm: document.getElementById('uploadForm'),
        modal: document.getElementById('messageModal'),
        modalTitle: document.getElementById('modalTitle'),
        modalMessage: document.getElementById('modalMessage'),
        modalCloseBtn: document.getElementById('modalCloseBtn'),
        uploadSummary: document.getElementById('upload-summary'),
        uploadCount: document.getElementById('upload-count'),
        completedCount: document.getElementById('completed-count'),
        description: document.getElementById('description')
    };

    // State
    const state = {
        uploads: [],
        completedUploads: 0
    };

    // Initialize
    initEventListeners();
    checkUrlParams();

    function initEventListeners() {
        if (elements.fileInput) {
            elements.fileInput.addEventListener('change', handleFileSelect);
        }

        if (elements.dropzone) {
            ['dragover', 'dragleave', 'drop'].forEach(eventName => {
                elements.dropzone.addEventListener(eventName, handleDragEvents);
            });
        }

        if (elements.uploadForm) {
            elements.uploadForm.addEventListener('submit', handleFormSubmit);
        }

        if (elements.modalCloseBtn) {
            elements.modalCloseBtn.addEventListener('click', closeModal);
        }

        window.addEventListener('click', (e) => {
            if (e.target === elements.modal) closeModal();
        });
    }

    function handleFileSelect(e) {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            elements.dropzone.style.display = 'none';
            renderFileList(files);
            elements.fileList.style.display = 'block';
        } else {
            resetUpload();
        }
    }

    function handleDragEvents(e) {
        e.preventDefault();
        e.stopPropagation();

        if (e.type === 'dragover') {
            elements.dropzone.classList.add('hover');
        } else if (e.type === 'dragleave') {
            elements.dropzone.classList.remove('hover');
        } else if (e.type === 'drop') {
            elements.dropzone.classList.remove('hover');
            handleDrop(e);
        }
    }

    function handleDrop(e) {
        const files = e.dataTransfer.files;
        const hasFolder = Array.from(files).some(file => file.size === 0 && file.type === "");

        if (hasFolder) {
            showModal('上传失败', '不支持上传文件夹，请选择具体文件', 'error');
            return;
        }

        elements.fileInput.files = files;
        elements.fileInput.dispatchEvent(new Event('change'));
    }

    async function handleFormSubmit(e) {
        e.preventDefault();

        const files = Array.from(elements.fileInput.files);
        const description = elements.description.value;
        const submitBtn = elements.uploadForm.querySelector('button[type="submit"]');

        if (files.length === 0) {
            showModal('上传失败', '请先选择要上传的文件', 'error');
            return;
        }

        // Disable submit button
        if (submitBtn) {
            submitBtn.disabled = true;
            const originalBtnContent = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 正在上传...';
            // Store original content to restore later
            submitBtn.dataset.originalContent = originalBtnContent;
        }

        // Reset state
        state.uploads = files.map(file => ({ file, status: 'pending', progress: 0 }));
        state.completedUploads = 0;

        // Update UI
        elements.uploadCount.textContent = files.length;
        elements.completedCount.textContent = '0';
        elements.uploadSummary.style.display = 'block';

        try {
            // Upload files concurrently
            const uploadPromises = files.map((file, index) => uploadFile(file, index, description));
            await Promise.allSettled(uploadPromises);
        } finally {
            // Re-enable submit button
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.dataset.originalContent || '<i class="fas fa-upload"></i> 上传文件';
            }
        }
    }

    function uploadFile(file, index, description) {
        return new Promise((resolve, reject) => {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('description', description);

            const password = document.getElementById('password').value;
            if (password) {
                formData.append('password', password);
            }

            const expiration = document.getElementById('expiration').value;
            formData.append('expiration', expiration);

            updateFileStatus(index, 'uploading', 0);

            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    updateFileProgress(index, percent);
                    if (percent === 100) {
                        updateFileStatus(index, 'processing');
                    }
                }
            });

            xhr.addEventListener('load', () => {
                try {
                    const result = JSON.parse(xhr.responseText);
                    if (result.success) {
                        updateFileStatus(index, 'success', 100);
                        state.completedUploads++;
                        elements.completedCount.textContent = state.completedUploads;

                        if (state.completedUploads === state.uploads.length) {
                            showModal('上传完成', `所有文件上传成功！共 ${state.completedUploads} 个文件`, 'success');
                            resetUpload();
                            elements.uploadForm.reset();
                        }
                        resolve(result);
                    } else {
                        updateFileStatus(index, 'error', 0, result.message);
                        state.completedUploads++;
                        elements.completedCount.textContent = state.completedUploads;
                        reject(new Error(result.message));
                    }
                } catch (error) {
                    updateFileStatus(index, 'error', 0, '解析响应失败');
                    state.completedUploads++;
                    elements.completedCount.textContent = state.completedUploads;
                    reject(error);
                }
            });

            xhr.addEventListener('error', () => {
                updateFileStatus(index, 'error', 0, '网络错误');
                state.completedUploads++;
                elements.completedCount.textContent = state.completedUploads;
                reject(new Error('Network error'));
            });

            xhr.open('POST', '/upload');
            xhr.send(formData);
        });
    }

    function renderFileList(files) {
        elements.fileList.innerHTML = files.map((file, index) => `
            <div class="file-item" data-index="${index}">
                <div class="file-header">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" id="progress-${index}" style="width: 0%">0%</div>
                </div>
                <div class="status" id="status-${index}">等待上传</div>
            </div>
        `).join('');
    }

    function updateFileProgress(index, percent) {
        const progressBar = document.getElementById(`progress-${index}`);
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.textContent = `${percent}%`;
        }
    }

    function updateFileStatus(index, status, progress, message = '') {
        const statusElement = document.getElementById(`status-${index}`);
        if (statusElement) {
            statusElement.className = `status ${status}`;

            const statusText = {
                'uploading': '上传中...',
                'processing': '正在保存，请勿关闭页面...',
                'success': '上传成功',
                'error': message || '上传失败',
                'pending': '等待上传'
            };
            statusElement.textContent = statusText[status] || statusText['pending'];

            // Reset color style first
            statusElement.style.color = '';

            if (status === 'processing') {
                statusElement.style.color = 'var(--primary-dark)';
            }
        }
    }

    function resetUpload() {
        elements.dropzone.style.display = 'block';
        elements.fileList.style.display = 'none';
        elements.fileList.innerHTML = '';
        elements.uploadSummary.style.display = 'none';
        elements.fileInput.value = '';
        // Clear uploads state
        state.uploads = [];
        state.completedUploads = 0;
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function showModal(title, message, type) {
        elements.modalTitle.textContent = title;
        elements.modalMessage.textContent = message;
        elements.modalTitle.className = type || '';
        elements.modalMessage.className = type || '';
        elements.modal.style.display = 'block';
    }

    function closeModal() {
        elements.modal.style.display = 'none';
    }

    function checkUrlParams() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('uploaded') === 'true') {
            showModal('上传成功', '文件上传成功！', 'success');
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }

    // Prevent accidental page close during upload
    window.addEventListener('beforeunload', (e) => {
        if (state.uploads.length > 0 && state.completedUploads < state.uploads.length) {
            e.preventDefault();
            e.returnValue = '文件正在上传中，确定要离开吗？';
        }
    });
});
