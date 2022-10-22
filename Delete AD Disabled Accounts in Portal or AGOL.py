# This script requires being on Python API 2.0.0 or higher due to BUG-000146804 “The licenses.all() function in the admin module does not return licenses when connected to Portal for ArcGIS”
# All URLS, Usernames, and Passwords are System Environmental Variables on the machine running the script and are then pulled using os.getenv to get the values
# While I haven’t tested it, I do not think that users have to enable SAML with their portals since we are querying based on the user’s email address.

from ldap3 import ALL
from ldap3 import Connection
from ldap3 import NTLM
from ldap3 import Server
from arcgis.gis import GIS
import os


# insert portal connections
# Set Environmental Variables for the URL, Admin User, and Password for each of your Portals
portals = {
    os.getenv('Portal1URL'):[os.getenv('Portal1User'),os.getenv('Portal1Secret')],
    os.getenv('Portal2URL'):[os.getenv('Portal2User'),os.getenv('Portal2Secret')],
    os.getenv('Portal3URL'):[os.getenv('Portal3User'),os.getenv('Portal3Secret')],
    os.getenv('AGOL1URL'):[os.getenv('AGOL1User'),os.getenv('AGOL1Secret')]
}

# Active Directory Portion of Python Script
Disabled_Accounts = list()

# Set Environmental Variables for the Domain Controller (ldap_DC), View Only User (ldap_user), and View Only User Password(ldap_secret).
DC = os.getenv('ldap_DC') #FQDN for Domain Controller
accessUser = os.getenv('ldap_user') #View Only User to Domain Controller
secret_pass = os.getenv('ldap_secret') #Password for View Only User to Domain Controller'
server = Server(f"{DC}", get_info=ALL, use_ssl=True)
conn = Connection(server, user=f"{accessUser}", password=f"{secret_pass}", authentication=NTLM, auto_bind=True)
QueryRoot = 'DC=ci,DC=visalia,DC=ca,DC=us' #Query Root from AD
Query = '(&(objectCategory=person)(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=2))' #Query from AD
conn.search(QueryRoot,Query,attributes=['cn', 'givenName', 'samaccountname', 'uid', 'userprincipalname','mail','whenChanged'])
users_ = conn.entries

for user in users_:
    Disabled_Accounts.append(str(user['mail']))

# ArcGIS Enterprise Portion of Python Script
for portal in portals:
    url = portal
    adminuser = portals[portal][0]
    adminpass = portals[portal][1]
    source = GIS(url,adminuser,adminpass,use_gen_token=True) # use_gen_token=True needed if you are wanting to use a built in account with Python API 2.0.0 and do not have built in accounts enabled on your Portal
    print('Processing '+url)
    sourceusers = source.users.search(max_users=1000)
    org_licenses=source.admin.license.all()
    org_bundles=source.admin.license.bundles
    for user in sourceusers:
        if user.email in Disabled_Accounts:
            account = user.username
            level = user.level
            lastLogin = user.lastLogin
            for license in org_licenses:
                try:
                    license.revoke(username=account,entitlements='*')
                except:
                    pass
            for bundle in org_bundles:
                try:
                    bundle.revoke(account)
                except:
                    pass
            print(account)
            print(level)
            print(lastLogin)
            print("deleting user: " + account)
            user.delete(reassign_to=adminuser) # reassigns any content deleted user had to the admin account used to delete.
            print("-----------------------")
