<template>
  <div>
    <a-tabs default-active-key="providers">
      <a-tab-pane key="providers" title="Model Management">
        <a-space style="margin-bottom: 16px;">
          <a-button type="primary" @click="showAddModal">Add Provider</a-button>
          <a-button @click="loadData">Refresh</a-button>
        </a-space>

        <a-table :data="providers" :pagination="false" row-key="id">
          <template #columns>
            <a-table-column title="Name" data-index="name" />
            <a-table-column title="API Base" data-index="api_base" />
            <a-table-column title="API Key" data-index="api_key_masked" />
            <a-table-column title="Models">
              <template #cell="{ record }">
                <a-tag v-for="m in record.models" :key="m.id" color="arcoblue">
                  {{ m.name || m.id }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="Status">
              <template #cell="{ record }">
                <a-tag :color="record.enabled ? 'green' : 'red'">
                  {{ record.enabled ? 'Enabled' : 'Disabled' }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="Actions">
              <template #cell="{ record }">
                <a-space>
                  <a-button size="small" @click="testProvider(record.id)" :loading="testing[record.id]">
                    Test
                  </a-button>
                  <a-button size="small" type="outline" @click="editProvider(record)">Edit</a-button>
                  <a-popconfirm content="Delete this provider?" @ok="deleteProvider(record.id)">
                    <a-button size="small" status="danger">Delete</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </template>
        </a-table>

        <!-- Available Models -->
        <a-divider />
        <h3>Available Models</h3>
        <a-table :data="models" :pagination="false" row-key="model_id">
          <template #columns>
            <a-table-column title="Provider" data-index="provider_name" />
            <a-table-column title="Model" data-index="model_name" />
            <a-table-column title="ID">
              <template #cell="{ record }">
                <a-tag>{{ record.provider_id }}/{{ record.model_id }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="Default">
              <template #cell="{ record }">
                <a-tag v-if="record.is_default" color="green">Default</a-tag>
              </template>
            </a-table-column>
          </template>
        </a-table>
      </a-tab-pane>

      <a-tab-pane key="preferences" title="Preferences">
        <a-form :model="prefs" style="max-width: 400px;">
          <a-form-item label="Theme">
            <a-switch v-model="isDark" @change="toggleTheme">
              <template #checked>Dark</template>
              <template #unchecked>Light</template>
            </a-switch>
          </a-form-item>
          <a-form-item label="MinerU Status">
            <a-tag :color="mineruOk ? 'green' : 'red'">
              {{ mineruOk ? 'Token Configured' : 'Token Missing' }}
            </a-tag>
          </a-form-item>
        </a-form>
      </a-tab-pane>
    </a-tabs>

    <!-- Add/Edit Modal -->
    <a-modal v-model:visible="modalVisible" :title="editingId ? 'Edit Provider' : 'Add Provider'" @ok="saveProvider">
      <a-form :model="form" layout="vertical">
        <a-form-item label="Provider ID" required>
          <a-input v-model="form.id" :disabled="!!editingId" />
        </a-form-item>
        <a-form-item label="Name" required>
          <a-input v-model="form.name" />
        </a-form-item>
        <a-form-item label="API Base URL" required>
          <a-input v-model="form.api_base" placeholder="https://api.openai.com/v1" />
        </a-form-item>
        <a-form-item label="API Key" required>
          <a-input-password v-model="form.api_key" />
        </a-form-item>
        <a-form-item label="Enabled">
          <a-switch v-model="form.enabled" />
        </a-form-item>
        <a-form-item label="Models">
          <div v-for="(m, i) in form.models" :key="i" style="display: flex; gap: 8px; margin-bottom: 8px;">
            <a-input v-model="m.id" placeholder="model-id" style="flex: 1;" />
            <a-input v-model="m.name" placeholder="Display Name" style="flex: 1;" />
            <a-button status="danger" @click="form.models.splice(i, 1)">Remove</a-button>
          </div>
          <a-button type="dashed" @click="form.models.push({ id: '', name: '', is_default: false })">
            Add Model
          </a-button>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Message } from '@arco-design/web-vue'
import { getProviders, addProvider, updateProvider, deleteProvider as deleteProviderApi, getModels, testProvider as testProviderApi } from '../api/settings'

const providers = ref([])
const models = ref([])
const testing = reactive({})
const mineruOk = ref(false)
const isDark = ref(false)
const modalVisible = ref(false)
const editingId = ref(null)
const form = reactive({
  id: '', name: '', api_base: '', api_key: '', enabled: true, models: []
})
const prefs = reactive({})

async function loadData() {
  try {
    const [p, m] = await Promise.all([getProviders(), getModels()])
    providers.value = p
    models.value = m
  } catch (e) {
    console.error('Failed to load settings:', e)
  }
}

function showAddModal() {
  editingId.value = null
  Object.assign(form, { id: '', name: '', api_base: '', api_key: '', enabled: true, models: [{ id: '', name: '', is_default: true }] })
  modalVisible.value = true
}

function editProvider(record) {
  editingId.value = record.id
  Object.assign(form, {
    id: record.id,
    name: record.name,
    api_base: record.api_base,
    api_key: '',
    enabled: record.enabled,
    models: record.models.map(m => ({ ...m })),
  })
  modalVisible.value = true
}

async function saveProvider() {
  try {
    if (editingId.value) {
      await updateProvider(editingId.value, form)
    } else {
      await addProvider(form)
    }
    modalVisible.value = false
    Message.success('Saved')
    loadData()
  } catch (e) {
    Message.error('Failed: ' + e.message)
  }
}

async function deleteProvider(id) {
  try {
    await deleteProviderApi(id)
    Message.success('Deleted')
    loadData()
  } catch (e) {
    Message.error('Failed: ' + e.message)
  }
}

async function testProvider(id) {
  testing[id] = true
  try {
    const result = await testProviderApi(id)
    if (result.ok) {
      Message.success('Connection OK: ' + (result.response || '').slice(0, 50))
    } else {
      Message.error('Failed: ' + result.error)
    }
  } catch (e) {
    Message.error('Failed: ' + e.message)
  } finally {
    testing[id] = false
  }
}

function toggleTheme(dark) {
  if (dark) {
    document.body.setAttribute('arco-theme', 'dark')
  } else {
    document.body.removeAttribute('arco-theme')
  }
}

onMounted(loadData)
</script>
