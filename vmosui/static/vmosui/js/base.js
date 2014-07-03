/*
 * This is the base Vmosui JavaScript object. There is only ever one of
 * these loaded (referenced as vmosui with a lower-case t) which happens
 * immediately after the definition below.
 *
 * Scripts that are dependent on functionality defined in the Vmosui object
 * must be included after this script in templates/base.html.
 */
var Vmosui = function () {
  var vmosui = {},
  initFunctions = [];

  /*
   * Use the addInitFunction() function to add initialization code which must
   * be called on DOM ready. This is useful for adding things like event
   * handlers or any other initialization functions which should preceed user
   * interaction but rely on DOM readiness.
   */
  vmosui.addInitFunction = function (fn) {
    initFunctions.push(fn);
  };

  /* Call all initialization functions and clear the queue. */
  vmosui.init = function () {
    for (var i = 0; i < initFunctions.length; i += 1) {
      initFunctions[i]();
    }

    /* Prevent multiple executions, just in case. */
    initFunctions = [];
  };

  return vmosui;
};

/* Create the one and only vmosui object. */
var vmosui = new Vmosui();
