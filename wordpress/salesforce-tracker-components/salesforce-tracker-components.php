<?php
/**
 * Plugin Name: ZarafyTek Salesforce Tracker Components
 * Description: Isolated Salesforce-only authenticated snapshot receiver and read-only quality-gated explorer for sftracker.zarafytek.com.
 * Version: 1.0.0
 * Requires PHP: 8.0
 */
if (!defined('ABSPATH')) { exit; }
require_once __DIR__ . '/includes/salesforce-snapshot-receiver.php';
require_once __DIR__ . '/includes/sf-phase1-snapshot-explorer.php';
