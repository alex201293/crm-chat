<?php
/**
 * Plugin Name: CRM Chat for WooCommerce
 * Description: Extends CRM Chat with WooCommerce customer data (name, email, order info).
 * Version: 1.0.0
 * Requires Plugins: crm-chat
 */

if (!defined('ABSPATH')) exit;

add_action('wp_footer', function() {
    if (!class_exists('WooCommerce')) return;
    if (!get_option('crm_chat_api_key')) return;

    $customer_name = '';
    $customer_email = '';

    if (is_user_logged_in()) {
        $user = wp_get_current_user();
        $customer_name = $user->display_name;
        $customer_email = $user->user_email;
    }

    if ($customer_name || $customer_email) {
        ?>
        <script>
        if (window.CRMChat) {
            // Enrich widget with WooCommerce customer data
            document.addEventListener('DOMContentLoaded', function() {
                if (window.CRMChat && window.CRMChat.init) {
                    // Widget already initialized by main plugin
                    // Pass customer info via localStorage for the widget
                    localStorage.setItem('crm_chat_visitor_name', <?php echo wp_json_encode($customer_name); ?>);
                    localStorage.setItem('crm_chat_visitor_email', <?php echo wp_json_encode($customer_email); ?>);
                }
            });
        }
        </script>
        <?php
    }
}, 99);
