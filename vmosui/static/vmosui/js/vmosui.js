vmosui.utils = {
  activateStep: function(button) {
    if (button.id != 'prepare-btn') {
      $('#prepare-menu').hide();
    }

    /* Visual pointer to the page contents. */
    var $button = $(button);
    if ($button.next().hasClass('btn-arrow-right')) {
      return;
    }

    /* De-activate previously active button. */
    $('div.btn-arrow-right').remove();
    $('button.active-step').removeClass('active-step');

    $button.addClass('active-step');
    $button.after('<div class="btn-arrow-right"></div>');
  },

  ajaxError: function(jqxhr, status, error) {
    /* Return error message. */
    var message = 'Error: ';
    if (jqxhr.status) {
      message += jqxhr.status + ' ' + error + '.';
      if (!message) {
        message += 'Unknown error.';
      }
    } else if (error == 'parsererror'){
      message += 'Parsing JSON request failed.';
    } else if (error == 'timeout'){
      message += 'Request timed out.';
    } else if (error == 'abort'){
      message += 'Request was aborted by the server.';
    } else {
      message += 'Unknown error.';
    }
    return message;
  },

  getFormCgid: function() {
    /* Get form's container_group id. */
    var regex = /(.+)-form/;
    var match = regex.exec($('#prepare-form').parents('div').attr('id'));
    return match[1];
  },

  getFormValues: function(form) {
    var $form = $(form);
    var values = {};
    $form.find('input').each(function(index) {
      var $input = $(this);
      /* Include checked checkbox inputs and all other input types. */
      if (!($input.attr('type') == 'checkbox') || $input.prop('checked')) {
        values[this.name] = $input.val();
      }
    });
    return values;
  },

  getNavCname: function(span) {
    /* Get clickable nav item's container name. */
    return $(span).parents('div.expand-collapse-groups')
                .prev('div.expand-collapse-container')
                .find('span.container-name').text();
  },

  loadGroup: function(containerName, groupName) {
    /* Return form for group. */
    $.ajax({
      url: '/prepare/group',
      data: { cname: containerName, gname: groupName },
      beforeSend: function(){
        $('#contents').empty();
        $('#loading').show();
      },
      complete: function(){
        $('#loading').hide();
      },
      success: function(response) {
        $('#contents').html(response);
      },
      error: function(jqxhr, status, error) {
        var message = vmosui.utils.ajaxError(jqxhr, status, error);
        $('#error-message').html(message);
      }
    });
  },

  updateConfigureLogView: function(configureType) {
    $.ajax({
      url: '/configure/tail/' + configureType,
      success: function(response) {
        if (response) {
          /* Show recent output and scroll to the bottom. */
          $('#configure-output').append(response);
          $('#configure-output').scrollTop($('#configure-output')[0]
            .scrollHeight);
        }

        setTimeout(function() {
          vmosui.utils.updateConfigureLogView(configureType);
        }, 2000);
      },
      error: function(jqxhr, status, error) {
        var message = vmosui.utils.ajaxError(jqxhr, status, error);
        $('#error-message').html(message);
      }
    });
  },

  updateDeployLogView: function(deployType) {
    $.ajax({
      url: '/deploy/tail/' + deployType,
      success: function(response) {
        if (response) {
          /* Show recent output and scroll to the bottom. */
          $('#deploy-output').append(response)
            .scrollTop($('#deploy-output')[0].scrollHeight);
        }

        setTimeout(function() {
          vmosui.utils.updateDeployLogView(deployType);
        }, 2000);
      },
      error: function(jqxhr, status, error) {
        var message = vmosui.utils.ajaxError(jqxhr, status, error);
        $('#error-message').html(message);
      }
    });
  }
};

vmosui.addInitFunction(function() {
  /* Hide loading indicator. */
  $('#loading').hide();

  /* Hide prepare-able menu items. */
  if (!$('#prepare-contents').length) {
    $('#prepare-menu').hide();
  }

  /* Show preparation forms. */
  $('#prepare-btn').click(function() {
    var $button = $(this);
    if ($button.hasClass('active-step')) {
      /* Nothing to do. */
      return;
    }

    vmosui.utils.activateStep(this);

    /* Show form for the first item. */
    $('#prepare-menu span.clickable').first().click();

    /* Allow user to expand or collapse each contianer in the nav. */
    $('div.expand-collapse-container').click(function() {
      var cid = this.id;
      $container = $(this);
      var $indicator = $container.find('div.collapsible');
      if (!$indicator.length) {
        $indicator = $container.find('div.expandable');
      }

      /* Toggle indicator and hide/show groups. */
      if ($indicator.hasClass('collapsible')) {
        $('#' + cid + '-groups').hide();
      } else {
        $('#' + cid + '-groups').show();
      }
      $indicator.toggleClass('collapsible');
      $indicator.toggleClass('expandable');
    });

    /* Show status of each group, indicating if there are missing values. */
    if (!$('#prepare-menu span.group-status').length) {
      $('#prepare-menu span.clickable').each(function() {
        var containerName = vmosui.utils.getNavCname(this);
        var $span = $(this);
        var groupName = $span.text();
        var cgid = this.id;

        $.ajax({
          url: '/prepare/status',
          data: { cname: containerName, gname: groupName },
          success: function(response) {
            $('#' + cgid).before(response);
          }
          /* Ignore errors. */
        });
      });
    }

    /* Show the list of items to prepare. */
    $('#prepare-menu').slideDown();
  });

  /* Retrieve page content based on button clicked. */
  $('button.actionable').click(function() {
    var $button = $(this);
    var action = $button.attr('action');
    if (!action || $button.hasClass('active-step')) {
      /* Nothing to do. */
      return;
    }

    vmosui.utils.activateStep(this);

    /* Clear old messages. */
    $('#messages div').empty();

    /* Fill in the page contents based on the action given. */
    $.ajax({
      url: action,
      beforeSend: function(){
        $('#contents').empty();
        $('#loading').show();
      },
      complete: function(){
        $('#loading').hide();
      },
      success: function(response) {
        $('#contents').html(response);
      },
      error: function(jqxhr, status, error) {
        var message = vmosui.utils.ajaxError(jqxhr, status, error);
        $('#error-message').html(message);
        $('#contents').empty();
      }
    });
  });

  /* Show form to set the group's answers. */
  $('#prepare-menu span.clickable').click(function() {
    /* Clear old messages. */
    $('#messages div').empty();

    var containerName = vmosui.utils.getNavCname(this);
    var $span = $(this);
    var groupName = $span.text();
    vmosui.utils.loadGroup(containerName, groupName);
  });

  /*
   * NOTE: Need to use "$(document).on(...)" to attach event handlers to
   * elements that will be loaded into the page later.
   */

  /* Submit form to set group's answers. */
  $(document).on('submit', '#prepare-form', function(event) {
    var $form = $(this);
    var action = $form.attr('action');
    var containerName = $('#prepare-form input[name="cname"]').val();
    var groupName = $('#prepare-form input[name="gname"]').val();

    /* Clear old messages. */
    $('#messages div').empty();

    $('#prepare-form button.btn-submit').button('loading');

    /* Send the data. */
    $.ajax({
      url: action,
      type: 'POST',
      data: vmosui.utils.getFormValues(this),
      success: function(response) {
        $('#success-message').html('Answer file updated.');
        $('#contents').html(response);

        /* Update group status indicator. */
        $.ajax({
          url: '/prepare/status',
          data: { cname: containerName, gname: groupName },
          success: function(response) {
            var cgid = vmosui.utils.getFormCgid();
            $('#' + cgid + '-status').replaceWith(response);
          },
          error: function(jqxhr, status, error) {
            /* Leave the status blank. */
            var cgid = vmosui.utils.getFormCgid();
            $('#' + cgid + '-status').empty();
          }
        });
      },
      error: function(jqxhr, status, error) {
        var message = vmosui.utils.ajaxError(jqxhr, status, error);
        $('#error-message').html(message);

        vmosui.utils.loadGroup(containerName, groupName);
      },
      complete: function(jqxhr, status, error) {
        $('#prepare-form button.btn-submit').button('reset');
      }
    });

    /* Prevent normal form submit action. */
    return false;
  });

  /* Reset to currently saved values. */
  $(document).on('click', '#prepare-form button.btn-reset', function() {
    var cgid = vmosui.utils.getFormCgid();
    $('#' + cgid).click();
  });

  /* Update log viewers periodically. */
  $('#deploy-nsx-btn').click(function() {
    setTimeout(function() {
      vmosui.utils.updateDeployLogView('nsx');
    }, 2000);
  });

  $('#configure-nsx-btn').click(function() {
    setTimeout(function() {
      vmosui.utils.updateConfigureLogView('nsx');
    }, 2000);
  });

  $('#deploy-sddc-btn').click(function() {
    setTimeout(function() {
      vmosui.utils.updateDeployLogView('sddc');
    }, 2000);
  });

  $('#configure-sddc-btn').click(function() {
    setTimeout(function() {
      vmosui.utils.updateConfigureLogView('sddc');
    }, 2000);
  });

  /* Start deployment. */
  $(document).on('click', '#deploy-validate, #deploy-run', function(event) {
    var values = vmosui.utils.getFormValues($('#deploy-form')[0]);
    var action = 'validate';
    if (this.id == 'deploy-run') {
        action = 'run';
    }
    values['action'] = action;

    var deployType = $('#deploy-form input[name="dtype"]').val();
    $.ajax({
      url: '/deploy/run/' + deployType,
      data: values,
      success: function(response) {
        $('#deploy-output').text(response);
       },
       error: function(jqxhr, status, error) {
         var message = vmosui.utils.ajaxError(jqxhr, status, error);
         $('#error-message').html(message);
       }      
    });

    /* Prevent normal form submit action. */
    return false;
  });

  /* Start configuration. */
  $(document).on('click', '#configure-validate, #configure-run',
                 function(event) {
    var values = vmosui.utils.getFormValues($('#configure-form')[0]);
    var action = 'validate';
    if (this.id == 'configure-run') {
        action = 'run';
    }
    values['action'] = action;

    var configureType = $('#configure-form input[name="ctype"]').val();
    $.ajax({
      url: '/configure/run/' + configureType,
      data: values,
      success: function(response) {
        $('#configure-output').text(response);
       },
       error: function(jqxhr, status, error) {
         var message = vmosui.utils.ajaxError(jqxhr, status, error);
         $('#error-message').html(message);
       }      
    });

    /* Prevent normal form submit action. */
    return false;
  });
});

$(document).ready(vmosui.init);
