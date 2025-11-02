

from time import sleep
from mxx.runner.core.callstack import MxxCallstack, PluginCallstackMeta
from mxx.runner.core.plugin import MxxPlugin
from mxx.runner.core.registry import MAPPINGS


class MxxRunner:
    def _exportCfgs(self, cfg : dict):
        """
        Export and separate plugin configs from global configs.
        
        Args:
            cfg: Configuration dictionary
        
        Returns:
            Tuple of (plugin_configs, global_configs)
            - plugin_configs: Dict of plugin_name -> plugin_config
            - global_configs: Dict of global configuration values
        """
        pcfg = {}
        gcfg = {}

        # Separate plugin-specific configs from global configs
        for k, v in cfg.items():
            if k in MAPPINGS:
                # This is a plugin configuration
                if isinstance(v, dict):
                    pcfg[k] = v
                else:
                    gcfg[k] = v
            else:
                # Could be a global config or unknown
                gcfg[k] = v

        return pcfg, gcfg

    def run(self, cfg : dict):
        """
        Run the MxxRunner with given configuration.
        
        Args:
            cfg: Configuration dictionary where keys are plugin names
                 and values are plugin-specific config dicts.
                 Example: {"lifetime": {"lifetime": 3600}, "os": {"cmd": "echo"}}
        """
        pcfg, gcfg = self._exportCfgs(cfg)
        self.gcfg = gcfg
        plugins = {}
        
        for plugin_name, plugin_cfg in pcfg.items():
            if plugin_name not in MAPPINGS:
                raise Exception(f"Plugin '{plugin_name}' is not registered")

            plugin_cls = MAPPINGS[plugin_name]
            plugin_instance = plugin_cls(**plugin_cfg)
            plugins[plugin_name] = plugin_instance

        self.plugins = plugins

        self.run_events(plugins)

    def run_events(self, plugins : dict[str, MxxPlugin]):
        callstack = MxxCallstack()
        for plugin in plugins.values():
            plugin_callstack = PluginCallstackMeta._callstackMap[plugin.__cmdname__]
            callstack.merge(plugin_callstack)

        try:
            # Check initial conditions
            # all_cond: all must return True (empty list = pass)
            # any_cond: at least one must return True (empty list = pass)
            all_cond_passed = all(self._run_action(cond) for cond in callstack.all_cond) if callstack.all_cond else True
            any_cond_passed = any(self._run_action(cond) for cond in callstack.any_cond) if callstack.any_cond else True

            if not all_cond_passed or not any_cond_passed:
                return

            # Execute pre-actions
            for pre_action in callstack.pre_action:
                self._run_action(pre_action)

            # Execute main actions
            for action in callstack.action:
                self._run_action(action)

            # Now run on_true/on_false loop
            # on_true: return True to continue, False to stop
            # on_false: return True to stop, False to continue
            # Loop continues while: all on_true return True AND all on_false return False
            # If no on_true/on_false hooks exist, skip the loop
            if callstack.on_true or callstack.on_false:
                while True:
                    should_continue = True
                    
                    # Check on_true hooks - if any return False, stop
                    if callstack.on_true:
                        if not all(self._run_action(ontrue) for ontrue in callstack.on_true):
                            should_continue = False
                    
                    # Check on_false hooks - if any return True, stop
                    if callstack.on_false:
                        if any(self._run_action(onfalse) for onfalse in callstack.on_false):
                            should_continue = False
                    
                    if not should_continue:
                        break
                    
                    sleep(0.5)

            # Execute post-actions (cleanup)
            for post_action in callstack.post_action:
                self._run_action(post_action)

        except Exception as e:
            for onerror in callstack.on_error:
                self.currentError = e
                self._run_action(onerror)

    def _run_action(self, func):
        # check wehther func takes an argument, if yes, pass self
        import inspect
        sig = inspect.signature(func)
        if len(sig.parameters) > 0:
            return func(self)
        return func()
    
