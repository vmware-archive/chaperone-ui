vmosui.utils = {
  ajaxError: function(jqxhr, status, error) {
    /* Return error message. */
    var message = '';
    if (jqxhr.status) {
      if (jqxhr.status == '401') {
        /* Redirect to login page. */
        window.location = '/login';
      }

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
    $('#error-message').html(message);
    return message;
  },

  clearMessages: function() {
    /* Clear old messages. */
    $('#messages div').empty();
  },

  confirmSave: function() {
    var $form = $('#prepare-form');
    if (!$form.hasClass('dirty')) {
      return;
    }
    var answer = confirm('Save changes?');
    if (answer == true) {
      vmosui.utils.saveGroup($form[0], false);
    }
  },

  getFormCgid: function() {
    /* Get form's container_group id. */
    var regex = /^(.+)-form$/;
    var match = regex.exec($('#prepare-form').closest('div').attr('id'));
    return match[1];
  },

  getFormValues: function(form) {
    var $form = $(form);
    message = '';

    /* Clear previous errors. */
    var errorClass = 'has-error';
    $form.find('div.form-field.' + errorClass).removeClass(errorClass);

    /* Form validation. */
    $form.find('input.file-checkbox:checked').each(function(index) {
      if (!$('#current-' + this.id).length && !$('#file-' + this.id).val()) {
        var $input = $(this);
        var section = $input.closest('div.form-section')
                        .find('div.form-section-title').text();
        var field = $input.parent().find('span.form-field-name').text();
        message += 'File missing for ' + section + ': ' + field + '.<br/>';
        $input.closest('div.form-field').addClass(errorClass);
      }
    });
    if (message) {
      $('#error-message').html(message);
      return null;
    }

    var values = new FormData(form);
    $form.find('input[type="checkbox"]').each(function(index) {
      var $input = $(this);
      if (!$input.prop('checked')) {
        /* Need to know if the checkbox is being unchecked. */
        values.append(this.name, '0');
      }
    });
    return values;
  },

  getNavCname: function(div) {
    /* Get clickable nav item's container name. */
    return $(div).closest('div.expand-collapse-groups')
             .prev('div.expand-collapse-container')
             .find('span.container-name').text();
  },

  loadGroup: function(containerName, groupName) {
    /* Return form for group. */
    vmosui.utils.clearMessages();
    $('#contents').empty();
    $('#loading').show();
    $.ajax({
      url: '/prepare/group',
      data: { cname: containerName, gname: groupName },
      success: function(response) {
        $('#contents').html(response);
      },
      error: function(jqxhr, status, error) {
        vmosui.utils.ajaxError(jqxhr, status, error);
      },
      complete: function() {
        $('#loading').hide();
      }
    });
  },

  loadVCenterOptions: function(knob, field, values) {
    var $field = $(field);
    /* Need CSRF token for Django POST requests. */
    var csrf = 'csrfmiddlewaretoken';
    values[csrf] = $('#vcenter-form input[name="' + csrf + '"]').val();

    $('#vcenter-errors').empty();
    var $knob = $(knob);
    if ($knob.attr('data-loading-text')) {
      $knob.button('loading');
    }
    $.ajax({
      url: '/options',
      type: 'POST',
      data: values,
      success: function(data) {
        if (data.errors && data.errors.length) {
          $('#vcenter-errors').html(data.errors.join('<br/>'));
          return;
        }

        /* Add options to input field. */
        $field.append('<option value="">-- select --</option>');
        for (var i = 0; i < data.options.length; i++) {
          var option = data.options[i];
          $field.append('<option value="' + option + '">' + option +
                        '</option>');
        }

        /* Show hidden inputs. */
        $field.parents('div.modal-section').find('div.no-display')
          .toggleClass('no-display display');
        if (!$('#vcenter-form').find('div.no-display').length) {
          $('div.modal-footer button[type="submit"]').show();
        }
        if ($knob.hasClass('btn-primary')) {
          $knob.toggleClass('btn-primary btn-secondary');
        }
      },
      error: function(jqxhr, status, error) {
        var message = vmosui.utils.ajaxError(jqxhr, status, error);
        $('#vcenter-errors').text(message);
      },
      complete: function(jqxhr, status, error) {
        if ($knob.attr('data-loading-text')) {
          $knob.button('reset');
        }
      },
    });
  },

  openLeftnavContainer: function(btnId) {
    var $button = $('#' + btnId);
    if ($button.hasClass('active-btn')) {
      /* Already on this. */
      return;
    }
    vmosui.utils.confirmSave();
    vmosui.utils.clearMessages();

    /* De-activate previously active button. */
    var prevId = $('#leftnav div.leftnav-btn.active-btn').attr('id');
    $('#' + prevId + '-menu').slideUp();
    $('#' + prevId).removeClass('active-btn');

    /* Activate new button. */
    $.cookie('activeButton', btnId);
    $button.addClass('active-btn');
    $('#' + btnId + '-menu').slideDown();

    if (btnId == 'prepare' &&
            !$('#prepare-menu span.group-status').first().html().length) {
      /* Show status of each group, indicating if there are missing values. */
      $.ajax({
        url: '/prepare/status',
        success: function(data) {
          $('#prepare-menu div.clickable').each(function(index) {
            var containerName = vmosui.utils.getNavCname(this);
            var $div = $(this);
            var groupName = $div.find('span.group-name').text();
            var cgid = this.id;

            if (data[containerName][groupName].complete) {
              $('#status-' + cgid).addClass('text-success').html('&#10004;');
            } else {
              $('#status-' + cgid).addClass('text-error').html('&#10008;');
            }
          });
        }
        /* Ignore errors. */
      });
    }

    /* Show contents for last item viewed. Default to first item. */
    var itemId = $.cookie(btnId + 'Item');
    if (!itemId || !$('#' + itemId).length) {
      itemId = $('#' + btnId + '-menu div.clickable').first().attr('id');
    }
    vmosui.utils.openLeftnavItem(itemId);
  },

  openLeftnavItem: function(itemId) {
    /* Note which item was last viewed. */
    vmosui.utils.clearMessages();
    var $div = $('#' + itemId);
    var activeClass = 'active-item';
    $('#leftnav div.clickable.' + activeClass).removeClass(activeClass);
    $div.addClass(activeClass);
    var buttonId = $div.closest('div.menu').prev('#leftnav div.leftnav-btn')
                     .attr('id');
    $.cookie(buttonId + 'Item', $div.attr('id'));

    if ($div.parents('#prepare-menu').length) {
      /* Show form to set the group's answers. */
      var containerName = vmosui.utils.getNavCname($div[0]);
      var groupName = $div.find('span.group-name').text();
      vmosui.utils.loadGroup(containerName, groupName);
    }

    if ($div.hasClass('actionable')) {
      /* Retrieve page content based on button clicked. */
      var action = $div.attr('data-action');
      if (!action || $div.hasClass('active-btn')) {
        /* Nothing to do. */
        return;
      }

      /* Fill in the page contents based on the action given. */
      $('#loading').show();
      var id = itemId;
      /* Add parent div first, so other functions know what page this is. */
      $('#contents').html('<div id="' + id +'-contents"></div>');
      $.ajax({
        url: action,
        success: function(response) {
          $('#' + id + '-contents').html(response);
          $('#contents div.form-group-title').append(' ' + $div.text());
        },
        error: function(jqxhr, status, error) {
          vmosui.utils.ajaxError(jqxhr, status, error);
          $('#contents').empty();
        },
        complete: function(){
          $('#loading').hide();
        }
      });
    }

    if ($div.hasClass('btn-command')) {
      /* Update log viewers periodically. */
      var idArr = itemId.split('-');
      var commandType = idArr[0];
      var thingType = idArr[1];

      if (commandType == 'configure') {
        setTimeout(function() {
          vmosui.utils.updateConfigureLogView(thingType);
        }, 2000);
      } else {
        setTimeout(function() {
          vmosui.utils.updateDeployLogView(thingType);
        }, 2000);
      }
    }
  },

  saveGroup: function(form, resetContents) {
    var $form = $(form);
    var action = $form.attr('action');
    var containerName = $('#prepare-form input[name="cname"]').val();
    var groupName = $('#prepare-form input[name="gname"]').val();
    var values = vmosui.utils.getFormValues(form);
    if (!values) {
        return false;
    }
    var cgid = vmosui.utils.getFormCgid();

    /* Send the data. */
    vmosui.utils.clearMessages();
    $('#prepare-save').button('loading');
    $('#status-' + cgid).hide();
    $('#loading-' + cgid).show();
    $.ajax({
      url: action,
      type: 'POST',
      data: values,
      success: function(data) {
        if (data.errors && data.errors.length) {
          $('#error-message').html(data.errors.join('<br/>'));
          return;
        }

        if (resetContents) {
          $('#contents').html(data.group);
        }

        if (data.complete != null) {
          var $indicator = $('#status-' + cgid);
          var missingClass = 'text-error';
          var completeClass = 'text-success';

          if (data.complete && $indicator.hasClass(missingClass)) {
            $indicator.toggleClass(missingClass + ' ' + completeClass)
              .html('&#10004;')
          } else if (!data.complete && $indicator.hasClass(completeClass)) {
            $indicator.toggleClass(missingClass + ' ' + completeClass)
              .html('&#10008;');
          }
        }
      },
      error: function(jqxhr, status, error) {
        vmosui.utils.ajaxError(jqxhr, status, error);
      },
      complete: function(jqxhr, status, error) {
        $('#loading-' + cgid).hide();
        $('#status-' + cgid).show();
        $('#prepare-save').button('reset');
      },
      /* Need these for sending FormData. */
      processData: false,
      contentType: false
    });
  },

  updateConfigureLogView: function(configureType) {
    $.ajax({
      url: '/configure/tail/' + configureType,
      success: function(response) {
        /* Show recent output and scroll to the bottom. */
        var $output = $('#configure-' + configureType + '-output');
        if (response && $output.length && response != $output.text()) {
          $output.text(response).scrollTop($output[0].scrollHeight);
        }

        /* Schedule another update, if we're still on the page. */
        if ($('#configure-' + configureType + '-contents').length) {
          setTimeout(function() {
            vmosui.utils.updateConfigureLogView(configureType);
          }, 2000);
        }
      },
      error: function(jqxhr, status, error) {
        vmosui.utils.ajaxError(jqxhr, status, error);
      }
    });
  },

  updateDeployLogView: function(deployType) {
    $.ajax({
      url: '/deploy/tail/' + deployType,
      success: function(response) {
        /* Show recent output and scroll to the bottom. */
        var $output = $('#deploy-' + deployType + '-output');
        if (response && $output.length && response != $output.text()) {
          $output.text(response).scrollTop($output[0].scrollHeight);
        }

        /* Schedule another update, if we're still on the page. */
        if ($('#deploy-' + deployType + '-contents').length) {
          setTimeout(function() {
            vmosui.utils.updateDeployLogView(deployType);
          }, 2000);
        }
      },
      error: function(jqxhr, status, error) {
        vmosui.utils.ajaxError(jqxhr, status, error);
      }
    });
  }
};

vmosui.addInitFunction(function() {
  /* Populate vCenter input field's choices. */
  $('#vcenter-form button.connect-btn').click(function(event) {
    var $button = $(this);
    var fieldId = $button.parents('div.form-field').attr('id');
    var $field = $('#id_' + fieldId);

    var regex = /^(.+?)_(.+)$/;
    var match = regex.exec(fieldId);
    var ftype = match[1];

    /* Get login info. */
    var vcenter = $('#id_' + ftype + '_vc').val();
    var username = $('#id_' + ftype + '_vc_username').val();
    var password = $('#id_' + ftype + '_vc_password').val();
    if (!vcenter || !username || !password) {
      $('#vcenter-errors').text('Host, user, and password required.');
      return;
    }
    var values = { fid: fieldId, vcenter: vcenter, username: username,
                   password: password, datacenter: '' };

    /* Clear out input field's choices. */
    $field.empty();
    var targetId = $field.attr('data-target');
    if (targetId) {
      /* Clear out target input field's choices. */
      var $target = $('#id_' + targetId);
      $target.empty();
    }
    vmosui.utils.loadVCenterOptions(this, $field[0], values);
  });

  /* Populate vCenter target input field's choices. */
  $('#vcenter-form select[data-target]').change(function(event) {
    var $select = $(this);
    var fieldId = $select.parents('div.form-field').attr('id');

    var regex = /^(.+?)_(.+)$/;
    var match = regex.exec(fieldId);
    var ftype = match[1];

    /* Get login info. */
    var vcenter = $('#id_' + ftype + '_vc').val();
    var username = $('#id_' + ftype + '_vc_username').val();
    var password = $('#id_' + ftype + '_vc_password').val();
    if (!vcenter || !username || !password) {
      $('#vcenter-errors').text('Host, user, and password required.');
      return;
    }
    var datacenter = $('#id_' + ftype + '_vc_datacenter').val();
    var targetId = $select.attr('data-target');
    var values = { fid: targetId, vcenter: vcenter, username: username,
                   password: password, datacenter: datacenter, cluster: '' };

    /* Clear out target input field's choices. */
    var $target = $('#id_' + targetId);
    $target.empty();
    vmosui.utils.loadVCenterOptions(this, $target[0], values);
  });

  /* Reset vCenter target input fields. */
  $('#vcenter-form input.vc-login').change(function(event) {
    var $field = $(this);
    var $section = $field.parents('div.modal-section');
    $section.find('div.display').toggleClass('display no-display');

    $('div.modal-footer button[type="submit"]').hide();
    var $knob = $section.find('button.connect-btn');
    if ($knob.hasClass('btn-secondary')) {
      $knob.toggleClass('btn-secondary btn-primary');
    }
  });

  /* Submit form to set vCenter settings. */
  $('#vcenter-form').submit(function(event) {
    var $form = $(this);
    var action = $form.attr('action');
    var values = vmosui.utils.getFormValues(this);
    if (!values) {
        return false;
    }

    /* Send the data. */
    $('#vcenter-errors').empty();
    $('#vcenter-save').button('loading');
    $.ajax({
      url: action,
      type: 'POST',
      data: values,
      success: function(data) {
        if (data.errors || data.field_errors) {
          /* General errors. */
          if (data.errors && data.errors.length) {
            $('#vcenter-errors').html(data.errors.join('<br/>'));
          }
          /* Field errors. */
          if (data.errors) {
            for (field in data.field_errors) {
              $('#error-' + field).parent().addClass('has-error');
              $('#error-' + field).addClass('text-error')
                .text(data.errors[field]);
            }
          }
          return;
        }

        /* Show contents for leftnav button last viewed. Default to first button. */
        var activeButton = $.cookie('activeButton');
        if (!activeButton || !$('#' + activeButton).length) {
          activeButton = $('#leftnav div.leftnav-btn').first().attr('id');
        }
        vmosui.utils.openLeftnavContainer(activeButton);

        /* Remove modal. */
        $('#modal-vcenter').remove();
        $('#backdrop-vcenter').remove();
      },
      error: function(jqxhr, status, error) {
        var message = vmosui.utils.ajaxError(jqxhr, status, error);
        $('#vcenter-errors').text(message);
      },
      complete: function(jqxhr, status, error) {
        $('#vcenter-save').button('reset');
      },
      /* Need these for sending FormData. */
      processData: false,
      contentType: false
    });

    /* Prevent normal form submit action. */
    return false;
  });

  /* Allow user to expand or collapse each contianer in the nav. */
  $('#prepare-menu div.expand-collapse-container').click(function(event) {
    var cid = this.id;
    $container = $(this);
    var $knob = $container.find('div.collapsible');
    if (!$knob.length) {
      $knob = $container.find('div.expandable');
    }

    /* Toggle expande/collapse knob and hide/show groups. */
    $('#groups-' + cid).toggle();
    $knob.toggleClass('collapsible');
    $knob.toggleClass('expandable');
  });

  /*
   * NOTE: Need to use "$(document).on(...)" to attach event handlers to
   * elements that will be loaded into the page later.
   */

  /* Indicate when there are changes made in the form before saving. */
  $(document).on('change', '#prepare-form input:not(.password-checkbox), ' +
                 '#prepare-form select', function(event) {
    var text = $('div.form-group-title').text();
    var suffix = ' *';
    if (text.indexOf(suffix, text.length - suffix.length) == -1) {
      $('#prepare-form').addClass('dirty');
      $('div.form-group-title').append(suffix);
    }
  });

  /* Show/hide elements based on state of other elements. */
  $(document).on('change',
                 '#prepare-form input.toggle-show', function(event) {
    /* Toggle the inputs related to file uploads. */
    var $input = $(this);
    if ($input.hasClass('file-checkbox')) {
      $('#file-field-' + this.id).toggle();
    }

    if ($input.attr('data-show')) {
      /* CSV list of ids of elements to show/hide. */
      var data;
      var ids = $input.attr('data-show').split(',');
      for (var i = 0; i < ids.length; i++) {
        var target = ids[i].trim();
        $('#form-field-' + target).toggle();
      }
    }
  });

  /* Show/hide password in clear text. */
  $(document).on('change',
                 '#vcenter-form input.toggle-show.password-checkbox, ' +
                 '#prepare-form input.toggle-show.password-checkbox',
                 function(event) {
    var $knob = $(this);
    var $input = $knob.closest('div.form-field')
                   .find('input[type="password"], input[type="text"]');

    if ($input.attr('type') == 'password') {
      $input.attr('type', 'text');
    } else {
      $input.attr('type', 'password');
    }
  });

  /* Show/hide other elements based on selected option. */
  $(document).on('change', '#prepare-form select.toggle-show',
                 function(event) {
    var $select = $(this);
    var $option = $select.find('option:selected');

    if ($option.attr('data-hide')) {
      /* CSV list of ids of elements to hide. */
      var data;
      var ids = $option.attr('data-hide').split(',');
      for (var i = 0; i < ids.length; i++) {
        var target = ids[i].trim();
        $('#form-field-' + target).hide();
      }
    }

    if ($option.attr('data-show')) {
      /* CSV list of ids of elements to show. */
      var data;
      var ids = $option.attr('data-show').split(',');
      for (var i = 0; i < ids.length; i++) {
        var target = ids[i].trim();
        $('#form-field-' + target).show();
      }
    }
  });

  /* Reset form. */
  $(document).on('click', '#prepare-reset', function(event) {
    /*
     * Reload entire contents versus only the input value, because the
     * display of shown/hidden fields also needs to be reset.
     */
    var cgid = vmosui.utils.getFormCgid();
    vmosui.utils.openLeftnavItem(cgid);
    return false;
  });

  /* Submit form to save group's answers. */
  $(document).on('submit', '#prepare-form', function(event) {
    vmosui.utils.saveGroup(this, true);
    /* Prevent normal form submit action. */
    return false;
  });

  /* Start deployment. */
  $(document).on('click', '#deploy-validate, #deploy-run', function(event) {
    var values = vmosui.utils.getFormValues($('#deploy-form')[0]);
    if (!values) {
        return false;
    }

    var action = 'validate';
    if (this.id == 'deploy-run') {
        action = 'run';
    }
    values.append('action', action);

    var deployType = $('#deploy-form input[name="dtype"]').val();
    var message = 'Starting to ' + action + '...\n';
    $('#deploy-' + deployType + '-output').text(message);

    $.ajax({
      url: '/deploy/run/' + deployType,
      type: 'POST',
      data: values,
      error: function(jqxhr, status, error) {
        vmosui.utils.ajaxError(jqxhr, status, error);
      },
      /* Need these for sending FormData. */
      processData: false,
      contentType: false
    });

    /* Prevent normal form submit action. */
    return false;
  });

  /* Start configuration. */
  $(document).on('click', '#configure-validate, #configure-run',
                 function(event) {
    var values = vmosui.utils.getFormValues($('#configure-form')[0]);
    if (!values) {
        return false;
    }

    var action = 'validate';
    if (this.id == 'configure-run') {
        action = 'run';
    }
    values.append('action', action);

    var configureType = $('#configure-form input[name="ctype"]').val();
    /* Create area for output, if it doesn't exist. */
    if (!$('#configure-' + configureType + '-output').length) {
      var pre = '<pre id="configure-' + configureType +
                '-output" class="command-output"></pre>';
      $('#configure-' + configureType + '-contents').append(pre);

      /* Scroll to the output so user sees it exists. */
      $('html').scrollTop($('#configure-' + configureType +
                            '-output').offset().top);
    }
    var message = 'Starting to ' + action + '...\n';
    $('#configure-' + configureType + '-output').text(message);

    $.ajax({
      url: '/configure/run/' + configureType,
      type: 'POST',
      data: values,
      error: function(jqxhr, status, error) {
        vmosui.utils.ajaxError(jqxhr, status, error);
      },
      /* Need these for sending FormData. */
      processData: false,
      contentType: false
    });

    /* Prevent normal form submit action. */
    return false;
  });

  /* Change active leftnav button. */
  $('#leftnav div.leftnav-btn').click(function(event) {
    vmosui.utils.openLeftnavContainer(this.id);
  });

  $('#leftnav div.clickable').click(function(event) {
    vmosui.utils.confirmSave();
    vmosui.utils.openLeftnavItem(this.id);
  });

  /* Warnings to user when leaving the page. */
  $(window).bind('beforeunload', function(event) {
    if ($('#prepare-form').hasClass('dirty')) {
      return 'There are unsaved changes.';
    }
  });
});

$(document).ready(vmosui.init);
