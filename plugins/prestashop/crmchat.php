<?php
/**
 * CRM Chat - PrestaShop Module
 * Installs the AI chat widget on your PrestaShop store.
 */

if (!defined('_PS_VERSION_')) exit;

class CrmChat extends Module {
    public function __construct() {
        $this->name = 'crmchat';
        $this->tab = 'front_office_features';
        $this->version = '1.0.0';
        $this->author = 'CRM Chat';
        $this->need_instance = 0;
        $this->bootstrap = true;

        parent::__construct();

        $this->displayName = $this->l('CRM Chat');
        $this->description = $this->l('AI-powered chat widget for customer support.');
    }

    public function install() {
        return parent::install()
            && $this->registerHook('displayFooter')
            && Configuration::updateValue('CRM_CHAT_API_KEY', '')
            && Configuration::updateValue('CRM_CHAT_DOMAIN', 'https://api.crmchat.io')
            && Configuration::updateValue('CRM_CHAT_COLOR', '#2563eb')
            && Configuration::updateValue('CRM_CHAT_POSITION', 'bottom-right')
            && Configuration::updateValue('CRM_CHAT_LANGUAGE', 'es');
    }

    public function uninstall() {
        Configuration::deleteByName('CRM_CHAT_API_KEY');
        Configuration::deleteByName('CRM_CHAT_DOMAIN');
        Configuration::deleteByName('CRM_CHAT_COLOR');
        Configuration::deleteByName('CRM_CHAT_POSITION');
        Configuration::deleteByName('CRM_CHAT_LANGUAGE');
        return parent::uninstall();
    }

    public function getContent() {
        $output = '';
        if (Tools::isSubmit('submitCrmChat')) {
            Configuration::updateValue('CRM_CHAT_API_KEY', Tools::getValue('CRM_CHAT_API_KEY'));
            Configuration::updateValue('CRM_CHAT_DOMAIN', Tools::getValue('CRM_CHAT_DOMAIN'));
            Configuration::updateValue('CRM_CHAT_COLOR', Tools::getValue('CRM_CHAT_COLOR'));
            Configuration::updateValue('CRM_CHAT_POSITION', Tools::getValue('CRM_CHAT_POSITION'));
            Configuration::updateValue('CRM_CHAT_LANGUAGE', Tools::getValue('CRM_CHAT_LANGUAGE'));
            $output .= $this->displayConfirmation($this->l('Settings saved.'));
        }
        return $output . $this->renderForm();
    }

    private function renderForm() {
        $fields = [
            ['type' => 'text', 'label' => 'API Key', 'name' => 'CRM_CHAT_API_KEY', 'required' => true],
            ['type' => 'text', 'label' => 'Domain', 'name' => 'CRM_CHAT_DOMAIN'],
            ['type' => 'color', 'label' => 'Color', 'name' => 'CRM_CHAT_COLOR'],
            ['type' => 'select', 'label' => 'Position', 'name' => 'CRM_CHAT_POSITION', 'options' => [
                'query' => [['id' => 'bottom-right', 'name' => 'Bottom Right'], ['id' => 'bottom-left', 'name' => 'Bottom Left']],
                'id' => 'id', 'name' => 'name',
            ]],
            ['type' => 'text', 'label' => 'Language', 'name' => 'CRM_CHAT_LANGUAGE'],
        ];

        $helper = new HelperForm();
        $helper->submit_action = 'submitCrmChat';
        $helper->fields_value = [
            'CRM_CHAT_API_KEY' => Configuration::get('CRM_CHAT_API_KEY'),
            'CRM_CHAT_DOMAIN' => Configuration::get('CRM_CHAT_DOMAIN'),
            'CRM_CHAT_COLOR' => Configuration::get('CRM_CHAT_COLOR'),
            'CRM_CHAT_POSITION' => Configuration::get('CRM_CHAT_POSITION'),
            'CRM_CHAT_LANGUAGE' => Configuration::get('CRM_CHAT_LANGUAGE'),
        ];

        return $helper->generateForm([[
            'form' => [
                'legend' => ['title' => $this->l('CRM Chat Settings')],
                'input' => $fields,
                'submit' => ['title' => $this->l('Save')],
            ],
        ]]);
    }

    public function hookDisplayFooter() {
        $apiKey = Configuration::get('CRM_CHAT_API_KEY');
        if (empty($apiKey)) return '';

        $domain = Configuration::get('CRM_CHAT_DOMAIN');
        $color = Configuration::get('CRM_CHAT_COLOR');
        $position = Configuration::get('CRM_CHAT_POSITION');
        $language = Configuration::get('CRM_CHAT_LANGUAGE');

        return "<script src=\"{$domain}/widget/chat.js\"></script>
        <script>CRMChat.init({
            apiKey:'{$apiKey}',domain:'{$domain}',
            color:'{$color}',position:'{$position}',language:'{$language}'
        });</script>";
    }
}
