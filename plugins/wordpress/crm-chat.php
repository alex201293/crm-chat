<?php
/**
 * Plugin Name: CRM Chat
 * Plugin URI: https://crmchat.io
 * Description: AI-powered chat widget for customer support and sales.
 * Version: 1.0.0
 * Author: CRM Chat Team
 * License: GPL v2 or later
 * Text Domain: crm-chat
 */

if (!defined('ABSPATH')) exit;

define('CRM_CHAT_VERSION', '1.0.0');
define('CRM_CHAT_PLUGIN_DIR', plugin_dir_path(__FILE__));

class CRM_Chat_Plugin {
    private static $instance = null;

    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        add_action('wp_footer', [$this, 'inject_widget']);
    }

    public function add_admin_menu() {
        add_options_page(
            __('CRM Chat Settings', 'crm-chat'),
            __('CRM Chat', 'crm-chat'),
            'manage_options',
            'crm-chat',
            [$this, 'render_settings_page']
        );
    }

    public function register_settings() {
        register_setting('crm_chat_settings', 'crm_chat_api_key');
        register_setting('crm_chat_settings', 'crm_chat_domain');
        register_setting('crm_chat_settings', 'crm_chat_color');
        register_setting('crm_chat_settings', 'crm_chat_position');
        register_setting('crm_chat_settings', 'crm_chat_language');
        register_setting('crm_chat_settings', 'crm_chat_dark_mode');
    }

    public function render_settings_page() {
        ?>
        <div class="wrap">
            <h1><?php esc_html_e('CRM Chat Settings', 'crm-chat'); ?></h1>
            <form method="post" action="options.php">
                <?php settings_fields('crm_chat_settings'); ?>
                <table class="form-table">
                    <tr><th>API Key</th><td>
                        <input type="text" name="crm_chat_api_key"
                            value="<?php echo esc_attr(get_option('crm_chat_api_key')); ?>"
                            class="regular-text" required />
                    </td></tr>
                    <tr><th>Domain</th><td>
                        <input type="url" name="crm_chat_domain"
                            value="<?php echo esc_attr(get_option('crm_chat_domain', 'https://api.crmchat.io')); ?>"
                            class="regular-text" />
                    </td></tr>
                    <tr><th>Color</th><td>
                        <input type="color" name="crm_chat_color"
                            value="<?php echo esc_attr(get_option('crm_chat_color', '#2563eb')); ?>" />
                    </td></tr>
                    <tr><th>Position</th><td>
                        <select name="crm_chat_position">
                            <option value="bottom-right" <?php selected(get_option('crm_chat_position'), 'bottom-right'); ?>>Bottom Right</option>
                            <option value="bottom-left" <?php selected(get_option('crm_chat_position'), 'bottom-left'); ?>>Bottom Left</option>
                        </select>
                    </td></tr>
                    <tr><th>Language</th><td>
                        <input type="text" name="crm_chat_language"
                            value="<?php echo esc_attr(get_option('crm_chat_language', 'es')); ?>"
                            class="small-text" />
                    </td></tr>
                    <tr><th>Dark Mode</th><td>
                        <select name="crm_chat_dark_mode">
                            <option value="auto" <?php selected(get_option('crm_chat_dark_mode'), 'auto'); ?>>Auto</option>
                            <option value="light" <?php selected(get_option('crm_chat_dark_mode'), 'light'); ?>>Light</option>
                            <option value="dark" <?php selected(get_option('crm_chat_dark_mode'), 'dark'); ?>>Dark</option>
                        </select>
                    </td></tr>
                </table>
                <?php submit_button(); ?>
            </form>
        </div>
        <?php
    }

    public function inject_widget() {
        $api_key = get_option('crm_chat_api_key');
        if (empty($api_key)) return;

        $domain = esc_attr(get_option('crm_chat_domain', 'https://api.crmchat.io'));
        $color = esc_attr(get_option('crm_chat_color', '#2563eb'));
        $position = esc_attr(get_option('crm_chat_position', 'bottom-right'));
        $language = esc_attr(get_option('crm_chat_language', 'es'));
        $dark_mode = esc_attr(get_option('crm_chat_dark_mode', 'auto'));

        ?>
        <script src="<?php echo esc_url($domain); ?>/widget/chat.js"></script>
        <script>
        CRMChat.init({
            apiKey: '<?php echo esc_js($api_key); ?>',
            domain: '<?php echo esc_js($domain); ?>',
            color: '<?php echo esc_js($color); ?>',
            position: '<?php echo esc_js($position); ?>',
            language: '<?php echo esc_js($language); ?>',
            darkMode: '<?php echo esc_js($dark_mode); ?>'
        });
        </script>
        <?php
    }
}

CRM_Chat_Plugin::instance();
