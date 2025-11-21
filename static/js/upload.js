document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    const dropzone = document.getElementById('dropzone');
    const fileList = document.getElementById('file-list');
    const uploadForm = document.getElementById('uploadForm');
    const modal = document.getElementById('messageModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    const uploadSummary = document.getElementById('upload-summary');
    const uploadCount = document.getElementById('upload-count');
    const completedCount = document.getElementById('completed-count');

    // 存储上传状态
    let uploads = [];
    let completedUploads = 0;

    // 文件选中后
    if (fileInput) {
        fileInput.addEventListener('change', function (e) {
            const files = Array.from(e.target.files);
            if (files.length > 0) {
                dropzone.style.display = 'none';
                renderFileList(files);
                fileList.style.display = 'block';
            } else {
                resetUpload();
            }
        });
    }

    // 渲染文件列表
    function renderFileList(files) {
        fileList.innerHTML = '';

        files.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.dataset.index = index;

            fileItem.innerHTML = `
                <div class="file-header">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" id="progress-${index}">0%</div>
                </div>
                <div class="status" id="status-${index}">等待上传</div>
            `;

            fileList.appendChild(fileItem);
        });
    }

    // 拖拽到虚线框时
    if (dropzone) {
        dropzone.addEventListener('dragover', function (e) {
            e.preventDefault();
            dropzone.classList.add('hover');
        });

        dropzone.addEventListener('dragleave', function () {
            dropzone.classList.remove('hover');
        });

        dropzone.addEventListener('drop', function (e) {
            e.preventDefault();
            dropzone.classList.remove('hover');

            const files = e.dataTransfer.files;

            // 检查是否拖拽了文件夹
            const hasFolder = Array.from(files).some(file => file.size === 0 && file.type === "");
            if (hasFolder) {
                showModal('上传失败', '不支持上传文件夹，请选择具体文件', 'error');
                return;
            }

            fileInput.files = files;
            const event = new Event('change');
            fileInput.dispatchEvent(event);
        });
    }

    // 表单提交
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const files = Array.from(fileInput.files);
            const description = document.getElementById('description').value;

            if (files.length === 0) {
                showModal('上传失败', '请先选择要上传的文件', 'error');
                return;
            }

            // 初始化上传状态
            uploads = files.map(file => ({
                file,
                status: 'pending',
                progress: 0
            }));

            completedUploads = 0;
            uploadCount.textContent = files.length;
            completedCount.textContent = '0';
            uploadSummary.style.display = 'block';

            // 并发上传所有文件
            files.forEach((file, index) => {
                uploadFile(file, index, description);
            });
        });
    }

    // 上传单个文件
    function uploadFile(file, index, description) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('description', description);

        // 更新状态为上传中
        updateFileStatus(index, 'uploading', 0);

        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', function (e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                updateFileProgress(index, percentComplete);
            }
        });

        xhr.addEventListener('load', function () {
            try {
                const result = JSON.parse(xhr.responseText);
                if (result.success) {
                    updateFileStatus(index, 'success', 100);
                    completedUploads++;
                    completedCount.textContent = completedUploads;

                    // 如果所有文件都上传完成
                    if (completedUploads === uploads.length) {
                        showModal('上传完成', `所有文件上传成功！共 ${completedUploads} 个文件`, 'success');
                        resetUpload();
                        uploadForm.reset();
                    }
                } else {
                    updateFileStatus(index, 'error', 0, result.message);
                    completedUploads++;
                    completedCount.textContent = completedUploads;
                }
            } catch (error) {
                updateFileStatus(index, 'error', 0, '解析服务器响应时出错');
                completedUploads++;
                completedCount.textContent = completedUploads;
            }
        });

        xhr.addEventListener('error', function () {
            updateFileStatus(index, 'error', 0, '上传过程中发生网络错误');
            completedUploads++;
            completedCount.textContent = completedUploads;
        });

        xhr.addEventListener('abort', function () {
            updateFileStatus(index, 'error', 0, '上传已被取消');
            completedUploads++;
            completedCount.textContent = completedUploads;
        });

        xhr.open('POST', '/upload');
        xhr.send(formData);
    }

    // 更新文件上传进度
    function updateFileProgress(index, percent) {
        const progressBar = document.getElementById(`progress-${index}`);
        if (progressBar) {
            progressBar.style.width = percent + '%';
            progressBar.textContent = percent + '%';
        }

        // 更新上传状态对象
        if (uploads[index]) {
            uploads[index].progress = percent;
        }
    }

    // 更新文件状态
    function updateFileStatus(index, status, progress, message = '') {
        const statusElement = document.getElementById(`status-${index}`);
        if (statusElement) {
            statusElement.className = `status ${status}`;

            switch (status) {
                case 'uploading':
                    statusElement.textContent = '上传中...';
                    break;
                case 'success':
                    statusElement.textContent = '上传成功';
                    break;
                case 'error':
                    statusElement.textContent = message || '上传失败';
                    break;
                default:
                    statusElement.textContent = '等待上传';
            }
        }

        // 更新上传状态对象
        if (uploads[index]) {
            uploads[index].status = status;
            uploads[index].progress = progress;
            if (message) {
                uploads[index].message = message;
            }
        }
    }

    // 关闭弹窗
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', function () {
            modal.style.display = 'none';
        });
    }

    // 点击弹窗外部关闭
    window.addEventListener('click', function (e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // 重置上传状态
    function resetUpload() {
        dropzone.style.display = 'block';
        fileList.style.display = 'none';
        fileList.innerHTML = '';
        uploadSummary.style.display = 'none';
        fileInput.value = '';
    }

    // 格式化文件大小
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 显示弹窗
    function showModal(title, message, type) {
        modalTitle.textContent = title;
        modalMessage.textContent = message;

        if (type === 'success') {
            modalTitle.className = 'success';
            modalMessage.className = 'success';
        } else if (type === 'error') {
            modalTitle.className = 'error';
            modalMessage.className = 'error';
        }

        modal.style.display = 'block';
    }

    // 检查URL参数显示上传成功消息
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('uploaded') === 'true') {
        showModal('上传成功', '文件上传成功！', 'success');
        // 清除URL参数
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});
