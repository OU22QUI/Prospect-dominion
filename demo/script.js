document.addEventListener('DOMContentLoaded', () => {
  const demoSection = document.getElementById('demo');
  const dialog = document.getElementById('demoDialog');
  const requestDemo = document.getElementById('requestDemo');
  const viewWorkflow = document.getElementById('viewWorkflow');
  const dialogWorkflow = document.getElementById('dialogWorkflow');
  const closeDialog = document.getElementById('closeDialog');

  const scrollToWorkflow = () => {
    if (demoSection) {
      demoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  viewWorkflow?.addEventListener('click', scrollToWorkflow);
  dialogWorkflow?.addEventListener('click', () => {
    dialog?.close();
    scrollToWorkflow();
  });
  closeDialog?.addEventListener('click', () => dialog?.close());
  requestDemo?.addEventListener('click', () => {
    if (dialog?.showModal) {
      dialog.showModal();
    } else {
      scrollToWorkflow();
    }
  });

  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });
});
