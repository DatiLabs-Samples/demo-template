import { useState } from 'react'
import TopNavigation from '@cloudscape-design/components/top-navigation'
import AppLayout from '@cloudscape-design/components/app-layout'
import ContentLayout from '@cloudscape-design/components/content-layout'
import Header from '@cloudscape-design/components/header'
import Container from '@cloudscape-design/components/container'
import SpaceBetween from '@cloudscape-design/components/space-between'
import Box from '@cloudscape-design/components/box'
import Button from '@cloudscape-design/components/button'
import StatusIndicator from '@cloudscape-design/components/status-indicator'

export default function App() {
  const [response, setResponse] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<'success' | 'error' | null>(null)

  const checkBackend = async () => {
    setLoading(true)
    setResponse(null)
    setStatus(null)
    try {
      const res = await fetch('/health')
      const data = await res.json()
      setResponse(JSON.stringify(data, null, 2))
      setStatus('success')
    } catch (e) {
      setResponse(e instanceof Error ? e.message : 'Connection failed')
      setStatus('error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <TopNavigation
        identity={{ href: '/', title: 'Demo App', logo: { src: '/dati-logo.png', alt: 'Dati' } }}
        utilities={[
          {
            type: 'menu-dropdown',
            text: 'User',
            iconName: 'user-profile',
            items: [{ id: 'signout', text: 'Sign out' }],
          },
        ]}
      />
      <AppLayout
        navigationHide={true}
        toolsHide={true}
        content={
          <ContentLayout
            header={
              <Header variant="h1" description="AWS Demo Template">
                Dashboard
              </Header>
            }
          >
            <SpaceBetween size="l">
              <Container header={<Header variant="h2">Backend Status</Header>}>
                <SpaceBetween size="m">
                  <SpaceBetween direction="horizontal" size="xs">
                    <Button variant="primary" loading={loading} onClick={checkBackend}>
                      Check Backend
                    </Button>
                    {status && (
                      <StatusIndicator type={status}>
                        {status === 'success' ? 'Connected' : 'Unreachable'}
                      </StatusIndicator>
                    )}
                  </SpaceBetween>
                  {response && (
                    <Box variant="code">{response}</Box>
                  )}
                </SpaceBetween>
              </Container>
            </SpaceBetween>
          </ContentLayout>
        }
      />
    </>
  )
}
