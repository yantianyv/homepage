document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
});

function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase();
    const cards = document.querySelectorAll('.card');
    let hasResults = false;

    document.querySelectorAll('.category-section').forEach(section => {
        // Reset display to allow filtering
        section.style.display = 'block';
    });

    cards.forEach(card => {
        const fileName = card.getAttribute('data-name').toLowerCase();
        if (fileName.includes(searchTerm)) {
            card.style.display = 'flex';
            const categorySection = card.closest('.category-section');
            if (categorySection) {
                categorySection.style.display = 'block';
                const categoryFiles = categorySection.querySelector('.category-files');
                if (categoryFiles) {
                    categoryFiles.classList.remove('collapsed');
                    categoryFiles.style.display = 'grid';
                }
                const categoryTitle = categorySection.querySelector('.category-title');
                if (categoryTitle) {
                    categoryTitle.classList.remove('collapsed');
                }
            }
            hasResults = true;
        } else {
            card.style.display = 'none';
        }
    });

    // Handle empty state
    const downloadSection = document.querySelector('#downloads-section');
    if (downloadSection) {
        let emptyState = downloadSection.querySelector('.empty-search-state');
        
        if (!hasResults && searchTerm) {
            if (!emptyState) {
                emptyState = document.createElement('div');
                emptyState.className = 'empty-state empty-search-state';
                emptyState.innerHTML = `
                    <i class="fas fa-search"></i>
                    <h3>No matching files found</h3>
                    <p>Try different keywords</p>
                `;
                downloadSection.appendChild(emptyState);
            }
            
            // Hide all categories if no results
            document.querySelectorAll('.category-section').forEach(section => {
                section.style.display = 'none';
            });
            
        } else {
            if (emptyState) {
                emptyState.remove();
            }
            
            if (!searchTerm) {
                // Reset view when search is cleared
                document.querySelectorAll('.category-section').forEach(section => {
                    section.style.display = 'block';
                });
                document.querySelectorAll('.card').forEach(card => {
                    card.style.display = 'flex';
                });
            }
        }
    }
}

function toggleCategory(button) {
    const section = button.closest('.category-section');
    const filesContainer = section.querySelector('.category-files');
    const icon = button.querySelector('.fa-chevron-down');
    
    if (filesContainer.style.display === 'none' || filesContainer.classList.contains('collapsed')) {
        filesContainer.classList.remove('collapsed');
        filesContainer.style.display = 'grid';
        button.classList.remove('collapsed');
        if (icon) icon.style.transform = 'rotate(0deg)';
    } else {
        filesContainer.classList.add('collapsed');
        filesContainer.style.display = 'none';
        button.classList.add('collapsed');
        if (icon) icon.style.transform = 'rotate(-90deg)';
    }
}

// Expose function to global scope for onclick handlers
window.toggleCategory = toggleCategory;
