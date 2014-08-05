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
  },

  clearMessages: function() {
    /* Clear old messages. */
    $('#messages div').empty();
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

  getNavCname: function(span) {
    /* Get clickable nav item's container name. */
    return $(span).closest('div.expand-collapse-groups')
             .prev('div.expand-collapse-container')
             .find('span.container-name').text();
  },

  loadGroup: function(containerName, groupName) {
    /* Return form for group. */
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

  updateConfigureLogView: function(configureType) {
    $.ajax({
      url: '/configure/tail/' + configureType,
      success: function(response) {
        /* Show recent output and scroll to the bottom. */
        var $output = $('#configure-' + configureType + '-output');
        if (response && $output.length) {
          $output.append(response).scrollTop($output[0].scrollHeight);
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
        if (response && $output.length) {
          $output.append(response).scrollTop($output[0].scrollHeight);
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
  /* Hide prepare-able menu items. */
  if (!$('#prepare-contents').length) {
    $('#prepare-menu').hide();
  }

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

  /* Show preparation forms. */
  $('#prepare-btn').click(function(event) {
    var $button = $(this);
    if ($button.hasClass('active-step')) {
      /* Nothing to do. */
      return;
    }

    vmosui.utils.activateStep(this);

    /* Show form for the first item. */
    $('#prepare-menu span.clickable').first().click();

    /* Show status of each group, indicating if there are missing values. */
    if (!$('#prepare-menu span.group-status').first().html().length) {
      $.ajax({
        url: '/prepare/status',
        success: function(data) {
          $('#prepare-menu span.clickable').each(function(index) {
            var containerName = vmosui.utils.getNavCname(this);
            var $span = $(this);
            var groupName = $span.text();
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

    /* Show the list of items to prepare. */
    $('#prepare-menu').slideDown();
  });

  /* Retrieve page content based on button clicked. */
  $('button.actionable').click(function(event) {
    var $button = $(this);
    var action = $button.attr('action');
    if (!action || $button.hasClass('active-step')) {
      /* Nothing to do. */
      return;
    }

    vmosui.utils.activateStep(this);
    vmosui.utils.clearMessages();

    /* Fill in the page contents based on the action given. */
    $('#contents').empty();
    $('#loading').show();
    $.ajax({
      url: action,
      success: function(response) {
        $('#contents').html(response);
      },
      error: function(jqxhr, status, error) {
        vmosui.utils.ajaxError(jqxhr, status, error);
        $('#contents').empty();
      },
      complete: function(){
        $('#loading').hide();
      }
    });
  });

  /* Show form to set the group's answers. */
  $('#prepare-menu span.clickable').click(function(event) {
    vmosui.utils.clearMessages();

    var containerName = vmosui.utils.getNavCname(this);
    var $span = $(this);
    var groupName = $span.text();
    vmosui.utils.loadGroup(containerName, groupName);
  });

  /*
   * NOTE: Need to use "$(document).on(...)" to attach event handlers to
   * elements that will be loaded into the page later.
   */

  /* Indicate when there are changes made in the form before saving. */
  $(document).on('change', '#prepare-form input', function(event) {
    var text = $('div.form-group-title').text();
    var suffix = ' *';
    if (text.indexOf(suffix, text.length - suffix.length) == -1) {
      $('div.form-group-title').append(suffix);
    }
  });

  /* Show/hide fields based on state of other fields. */
  $(document).on('change', '#prepare-form input.toggle-show', function(event) {
    var $knob = $(this);
    if ($knob.hasClass('file-checkbox')) {
      /* Toggle the inputs related to file uploads. */
      $('#file-field-' + this.id).toggle();
    } else {
      /* CSV list of ids of divs to show/hide. */
      var ids = $knob.attr('data-toggle-show').split(',');
      for (var i = 0; i < ids.length; i++) {
        var target = ids[i].trim();
        $('#form-field-' + target).toggle();
      }
    }
  });

  /* Reset form. */
  $(document).on('click', '#prepare-form button.btn-reset', function(event) {
    /*
     * Reload entire contents versus only the input value, because the
     * display of shown/hidden fields also needs to be reset.
     */
    var cgid = vmosui.utils.getFormCgid();
    $('#' + cgid).click();
    return false;
  });

  /* Submit form to save group's answers. */
  $(document).on('submit', '#prepare-form', function(event) {
    vmosui.utils.clearMessages();

    var $form = $(this);
    var action = $form.attr('action');
    var containerName = $('#prepare-form input[name="cname"]').val();
    var groupName = $('#prepare-form input[name="gname"]').val();
    var values = vmosui.utils.getFormValues(this);
    if (!values) {
        return false;
    }

    /* Send the data. */
    $('#prepare-form button.btn-submit').button('loading');
    $.ajax({
      url: action,
      type: 'POST',
      data: values,
      success: function(data) {
        if (data.errors && data.errors.length) {
          $('#error-message').html(data.errors.join('<br/>'));
          return;
        }

        $('#success-message').html('Answer file updated.');
        $('#contents').html(data.group);

        if (data.complete != null) {
          var cgid = vmosui.utils.getFormCgid();
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
        $('#prepare-form button.btn-submit').button('reset');
      },
      /* Need these for sending FormData. */
      processData: false,
      contentType: false
    });

    /* Prevent normal form submit action. */
    return false;
  });

  /* Update log viewers periodically. */
  $('button.btn-command').click(function(event) {
    vmosui.utils.clearMessages();

    var idArr = this.id.split('-');
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
    values['action'] = action;

    var deployType = $('#deploy-form input[name="dtype"]').val();
    var message = 'Starting to ' + action + ' ' + deployType +
                  ' deployment...\n';
    $('#deploy-' + deployType + '-output').text(message);

    $.ajax({
      url: '/deploy/run/' + deployType,
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
    values['action'] = action;

    var configureType = $('#configure-form input[name="ctype"]').val();
    /* Create area for output, if it doesn't exist. */
    if (!$('#configure-' + configureType + '-output').length) {
      var pre = '<pre id="configure-' + configureType + '-output"></pre>';
      $('#configure-' + configureType + '-contents').append(pre);
    }
    var message = 'Starting to ' + action + ' ' + configureType +
                  ' configuration...\n';
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

  /* Clone row to a new section of inputs to configure another hypervisor. */
  $(document).on('click', 'button.btn-hv-add', function(event) {
    var countCookie = 'hvcount';
    var newCount = parseInt($.cookie(countCookie)) + 1;
    $.cookie(countCookie, newCount);

    /* Copy template row, updating count in all the ids and names. */
    var $div = $('#hv-row-0').clone();
    var divId = $div.attr('id');
    $div.attr('id', divId.replace(/0$/, newCount));
    $div.find('[id]').each(function() {
      this.id = this.id.replace(/^(hv-.+-)0$/, '$1' + newCount);
    });
    $div.find('[name]').each(function() {
      this.name = this.name.replace(/^(hv-.+-)0$/, '$1' + newCount);
    });

    /* Copy input values. */
    var regex = /^hv-add-(.+)$/;
    var match = regex.exec(this.id);
    var current = match[1];
    var $row = $('#hv-row-' + current);
    regex = new RegExp('(hv-.+-)' + current);
    $row.find('input').each(function(index) {
      var $input = $(this);
      var name = this.name.replace(regex, '$1' + newCount);
      $div.find('input[name="' + name + '"]').val($input.val());
    });

    /* Reset bond mode selection. */
    $('#hv-bond-' + newCount).val('');
    /* Keep NIC input disabled. */
    $('#hv-nic-' + newCount).prop('disabled', true);

    $('#hv-row-' + current).after($div[0]);
  });

  /* Remove form to configure hypervisor. */
  $(document).on('click', 'button.btn-hv-remove', function(event) {
    /* Must have at least one row plus template on the page. */
    if ($('div.form-section').length == 2) {
      return;
    }

    var regex = /^hv-remove-(.+)$/;
    var match = regex.exec(this.id);
    var current = match[1];
    $('#hv-row-' + current).remove();
  });

  /* Enable NICs selection. */
  $(document).on('change',
                 '#configure-hvs-contents input.hv-host, ' +
                 '#configure-hvs-contents input.hv-user, ' +
                 '#configure-hvs-contents input.hv-password',
                 function(event) {
    var regex = /^hv-(.+)-(.+)$/;
    var match = regex.exec(this.id);
    var current = match[2];
    $('#hv-error-' + current).empty();

    /* Reset bond mode selection. */
    var $bond = $('#hv-bond-' + current);
    $bond.val('');
    var $nic = $('#hv-nic-' + current);

    var host = $('#hv-host-' + current).val();
    var user = $('#hv-user-' + current).val();
    var password = $('#hv-password-' + current).val();

    if (host && user && password) {
      /* Load list of NICs for this host. */
      var values = { host: host, user: user, password: password };
      /* Need CSRF token for Django POST requests. */
      var csrf = 'csrfmiddlewaretoken';
      values[csrf] = $('#configure-form input[name="' + csrf + '"]').val();

      $('#hv-loadnics-' + current).show()
      $.ajax({
        url: '/configure/hvs/nics',
        type: 'POST',
        data: values,
        success: function(data) {
          $nic.empty();

          var message = data.error
          var nics = data.nics
          if (message || !nics.length) {
            /* Couldn't retrieve NICs. */
            $nic.prop('disabled', true);
            $nic.empty();
            $nic.prop('multiple', false);
            if (message) {
              $('#hv-error-' + current).text('Error: ' + message + '.');
            }
            return;
          }

          nics.sort();
          for (var i = 0; i < nics.length; i++) {
            var nic = nics[i];
            $nic.append('<option value="' + nic + '">' + nic + '</option>');
          }

          /* Change input type in case bond mode chosen before NICs enabled. */
          if ($bond.find('option:selected').hasClass('multinic')) {
            $nic.prop('multiple', true);
          } else {
            $nic.prop('multiple', false);
          }
          $nic.prop('disabled', false);
        },
        error: function(jqxhr, status, error) {
          vmosui.utils.ajaxError(jqxhr, status, error);
        },
        complete: function() {
          $('#hv-loadnics-' + current).hide();
        }
      });
    } else {
      $nic.prop('disabled', true);
      $nic.empty();
      $nic.prop('multiple', false);
    }
  });

  /* Toggle multi-select for NICs, based on the bond mode value. */
  $(document).on('change',
                 '#configure-hvs-contents div.form-row-field select.hv-bond',
                 function(event) {
    var regex = /^hv-bond-(.+)$/;
    var match = regex.exec(this.id);
    var current = match[1];
    var $nic = $('#hv-nic-' + current);

    /* Ignore if NIC selection not available. */
    if ($nic.prop('disabled')) {
      return;
    }

    var $select = $(this);
    if ($select.find('option:selected').hasClass('multinic')) {
      $nic.prop('multiple', true);
    } else {
      $nic.prop('multiple', false);
    }
  });
});

$(document).ready(vmosui.init);
